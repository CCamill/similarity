#include <llvm/IR/LLVMContext.h>
#include <llvm/IR/Module.h>
#include <llvm/IRReader/IRReader.h>
#include <llvm/Support/SourceMgr.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/IR/GlobalVariable.h>
#include <llvm/IR/Type.h>
#include <llvm/IR/DerivedTypes.h>
#include <llvm/IR/Constants.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Bitcode/BitcodeWriter.h>
#include <iostream>
#include <fstream>
#include <nlohmann/json.hpp>

using namespace llvm;
using json = nlohmann::json;

// 将 TypeID 转换为类型名称字符串
std::string getTypeName(llvm::Type* type) {
    if (!type) return "unknown";
    if (type->isArrayTy() && type->getArrayElementType()->isIntegerTy(8)) {
        return "string";
    }
    switch (type->getTypeID()) {
        case llvm::Type::VoidTyID:      return "void";
        case llvm::Type::HalfTyID:       return "half";
        case llvm::Type::FloatTyID:      return "float";
        case llvm::Type::DoubleTyID:     return "double";
        case llvm::Type::X86_FP80TyID:   return "x86_fp80";
        case llvm::Type::FP128TyID:      return "fp128";
        case llvm::Type::PPC_FP128TyID:  return "ppc_fp128";
        case llvm::Type::LabelTyID:      return "label";
        case llvm::Type::MetadataTyID:   return "metadata";
        case llvm::Type::X86_MMXTyID:    return "x86_mmx";
        case llvm::Type::TokenTyID:      return "token";
        case llvm::Type::IntegerTyID:    return "integer";
        case llvm::Type::FunctionTyID:   return "function";
        case llvm::Type::StructTyID:     return "struct";
        case llvm::Type::ArrayTyID:      return "array";
        case llvm::Type::PointerTyID:    return "pointer";
        default:                         return "unknown";
    }
}
std::string sanitizeString(const std::string& str) {
    std::string sanitized;
    for (char ch : str) {
        if (ch >= 32 && ch <= 126) { // 只保留可打印ASCII字符
            sanitized += ch;
        } else {
            sanitized += "\\x" + llvm::utohexstr(static_cast<unsigned char>(ch));
        }
    }
    return sanitized;
}

// 递归提取全局变量的值（带深度限制）
json extractGlobalValue(llvm::Constant* constant, int depth = 0) {
    const int MAX_DEPTH = 10;
    if (depth > MAX_DEPTH) return "N/A (max recursion depth exceeded)";
    if (!constant) return "N/A";

    json value;

    if (auto* global_var = llvm::dyn_cast<llvm::GlobalVariable>(constant)) {
        if (global_var->hasInitializer()) {
            return extractGlobalValue(global_var->getInitializer(), depth + 1);
        } else {
            return "N/A";
        }
    } else if (auto* constant_expr = llvm::dyn_cast<llvm::ConstantExpr>(constant)) {
        // 处理 GetElementPtr 指令
        if (constant_expr->getOpcode() == llvm::Instruction::GetElementPtr) {
            if (constant_expr->getNumOperands() > 0) {
                llvm::Value* base = constant_expr->getOperand(0);
                if (auto* base_global = llvm::dyn_cast<llvm::GlobalVariable>(base)) {
                    return extractGlobalValue(base_global, depth + 1);
                }
            }
        }
        // 处理指向全局变量的指针
        if (constant_expr->getNumOperands() > 0) {
            llvm::Value* base = constant_expr->getOperand(0);
            if (auto* base_global = llvm::dyn_cast<llvm::GlobalVariable>(base)) {
                return extractGlobalValue(base_global, depth + 1);
            }
        }
        return "N/A";
    } else if (auto* constant_data = llvm::dyn_cast<llvm::ConstantDataSequential>(constant)) {
        if (constant_data->isString()) {
            std::string str = constant_data->getAsString().str();
            return sanitizeString(str); // 处理非UTF-8字符
        } else {
            json array_values = json::array();
            for (unsigned i = 0; i < constant_data->getNumElements(); ++i) {
                if (constant_data->getElementType()->isIntegerTy()) {
                    array_values.push_back(constant_data->getElementAsInteger(i));
                } else if (constant_data->getElementType()->isFloatingPointTy()) {
                    array_values.push_back(constant_data->getElementAsDouble(i));
                } else {
                    array_values.push_back("N/A");
                }
            }
            return array_values;
        }
    } else if (auto* constant_int = llvm::dyn_cast<llvm::ConstantInt>(constant)) {
        return std::to_string(constant_int->getZExtValue());
    } else if (auto* constant_fp = llvm::dyn_cast<llvm::ConstantFP>(constant)) {
        return std::to_string(constant_fp->getValueAPF().convertToDouble());
    } else if (auto* constant_agg = llvm::dyn_cast<llvm::ConstantAggregate>(constant)) {
        json array_values = json::array();
        for (unsigned i = 0; i < constant_agg->getNumOperands(); ++i) {
            llvm::Constant* operand = constant_agg->getAggregateElement(i);
            if (operand) {
                array_values.push_back(extractGlobalValue(operand, depth + 1));
            } else {
                array_values.push_back("N/A");
            }
        }
        return array_values;
    } else if (auto* constant_ptr = llvm::dyn_cast<llvm::ConstantPointerNull>(constant)) {
        return "nullptr";
    } else {
        return "N/A";
    }
}

// 提取全局变量信息
json extractGlobalVarInfo(llvm::GlobalVariable& global_var, int id) {
    json var_info;

    // 原始定义
    std::string raw_definition;
    llvm::raw_string_ostream raw_os(raw_definition);
    global_var.print(raw_os);
    var_info["raw_definition"] = raw_definition;

    // 变量名称
    std::string var_name = global_var.getName().str();
    if (var_name.empty()) {
        // 对于匿名变量，从原始定义提取名称（如 "@0"）
        raw_os << global_var;
        var_name = raw_os.str().substr(0, raw_os.str().find(' '));
    } else {
        // 对于命名变量，手动添加 "@" 前缀
        var_name = "@" + var_name;
    }
    var_info["var_name"] = var_name;

    // 变量值
    if (global_var.hasInitializer()) {
        llvm::Constant* initializer = global_var.getInitializer();
        var_info["value"] = extractGlobalValue(initializer);
    } else {
        var_info["value"] = "N/A";
    }

    // 变量值长度和类型
    llvm::Type* type = global_var.getValueType();
    if (type) {
        if (auto* array_type = llvm::dyn_cast<llvm::ArrayType>(type)) {
            std::string type_str;
            llvm::raw_string_ostream type_os(type_str);
            type->print(type_os);
            var_info["value_lens"] = type_str;
        } else {
            var_info["value_lens"] = "N/A";
        }
        var_info["type"] = getTypeName(type);
    } else {
        var_info["value_lens"] = "N/A";
        var_info["type"] = "unknown";
    }

    // 链接类型
    auto linkage = global_var.getLinkage();
    if (linkage == llvm::GlobalValue::ExternalLinkage) {
        var_info["linkage"] = "external";
    } else if (linkage == llvm::GlobalValue::InternalLinkage) {
        var_info["linkage"] = "internal";
    } else {
        var_info["linkage"] = "unknown";
    }

    var_info["id"] = id;

    return var_info;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        llvm::errs() << "Usage: " << argv[0] << " <IR file> <output JSON file>\n";
        return 1;
    }

    // 读取 IR 文件
    llvm::LLVMContext context;
    llvm::SMDiagnostic err;
    std::unique_ptr<llvm::Module> module = llvm::parseIRFile(argv[1], err, context);
    if (!module) {
        err.print(argv[0], llvm::errs());
        return 1;
    }

    // 提取全局变量信息
    json global_vars_json;
    int id = 1;
    for (auto& global_var : module->globals()) {
        try {
            json var_info = extractGlobalVarInfo(global_var, id++);
            global_vars_json[var_info["var_name"].get<std::string>()] = var_info;
        } catch (const std::exception& e) {
            llvm::errs() << "Error processing global variable: " << global_var.getName() << "\n";
            llvm::errs() << "Exception: " << e.what() << "\n";
        }
    }

    // 写入 JSON 文件
    std::ofstream output_file(argv[2]);
    if (!output_file.is_open()) {
        llvm::errs() << "Failed to open output file: " << argv[2] << "\n";
        return 1;
    }
    output_file << global_vars_json.dump(4);
    output_file.close();

    llvm::outs() << "Global variable information has been written to " << argv[2] << "\n";

    return 0;
}