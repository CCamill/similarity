#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/Value.h"
#include "llvm/IR/Constants.h"
#include <nlohmann/json.hpp>
#include <fstream>

using namespace llvm;
using json = nlohmann::json;

// 提取结构体信息并生成 JSON
json extractStructInfo(Module &module) {
    json structInfo = json::object(); // 使用对象存储结构体信息
    for (StructType *structType : module.getIdentifiedStructTypes()) {
        std::string structName = "%" + structType->getName().str();
        json elements = json::array(); // 存储结构体元素类型
        for (unsigned i = 0; i < structType->getNumElements(); ++i) {
            Type *elementType = structType->getElementType(i);
            std::string typeName;
            llvm::raw_string_ostream rso(typeName);
            elementType->print(rso); // 直接打印类型名称
            elements.push_back(typeName);
        }
        structInfo[structName] = elements; // 将结构体名称作为键，元素类型数组作为值
    }
    return structInfo;
}

// 提取全局变量信息并生成 JSON
json extractGlobalVarInfo(Module &module) {
    json globalVarInfo = json::object(); // 使用对象存储全局变量信息
    for (GlobalVariable &globalVar : module.getGlobalList()) {
        std::string globalVarName = "%" + globalVar.getName().str();
        std::string typeName;
        llvm::raw_string_ostream rso(typeName);
        globalVar.getType()->print(rso); // 直接打印类型名称
        json globalVarJson = json::array();
        globalVarJson.push_back(typeName); // 将类型名称存储到数组中
        if (globalVar.hasInitializer()) {
            if (auto *init = globalVar.getInitializer()) {
                std::string initName;
                llvm::raw_string_ostream initRso(initName);
                init->print(initRso); // 直接打印初始值
                globalVarJson.push_back(initName);
            }
        }
        globalVarInfo[globalVarName] = globalVarJson; // 将全局变量名称作为键，类型和初始值作为值
    }
    return globalVarInfo;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        errs() << "用法: " << argv[0] << " <input.ll>\n";
        return 1;
    }

    LLVMContext context;
    SMDiagnostic err;

    // 解析IR文件
    std::unique_ptr<Module> module = parseIRFile(argv[1], err, context);
    if (!module) {
        err.print(argv[0], errs());
        return 1;
    }

    // 提取结构体信息
    json structInfo = extractStructInfo(*module);

    // 写入结构体信息到 JSON 文件
    std::ofstream structFile(argv[2]);
    if (structFile.is_open()) {
        structFile << structInfo.dump(4); // 使用 4 个空格进行格式化
        structFile.close();
        errs() << (argv[2])<< "process succeed\n";
    } else {
        errs() << (argv[2])<< "process failed\n";
        return 1;
    }

    return 0;
}