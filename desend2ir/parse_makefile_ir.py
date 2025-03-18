import re
import os
import json
import shlex
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple
from tqdm import tqdm
from typing import Optional
# import flutes
import time 

# 常量定义
EXCLUDED_DIRS = ["/share/", "/build/", "/thirdparty/","/third_party/", "/include/", "/lib64/", 
                "/tests/", "/test/", "/testsuites/", "scripts/",
                "/lib-src/", "/libraries/", "/cmake-proxies/"]
OPTIMIZATION_LEVELS = ['-O0', '-O1', '-O2', '-O3', '-Os', '-Oz']
MAKEFILE_VARS = ['CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'CC', 'CXX', 'CPP']
SOURCE_EXTENSIONS = ('.c', '.cpp', '.cc')
HEADER_EXTENSIONS = ('.h', '.hpp')
BUILD_TIMEOUT = 300  # 5 分钟

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MakefileParser:
    """Makefile 解析器"""
    
    VAR_PATTERN = re.compile(r'^([a-zA-Z0-9_]+)\s*([:+]*)=\s*(.*?)(?:#.*)?$')
    CONTINUATION_PATTERN = re.compile(r'\\\s*$')
    
    def __init__(self, makefile_path: str):
        self.path = Path(makefile_path)
        self.variables = self._parse()
    
    def _parse(self) -> Dict[str, str]:
        """解析Makefile变量"""
        variables = {}
        current_var = None
        
        with open(self.path, 'r') as f:
            for line in f:
                line = line.rstrip('\n\\')
                
                # 处理变量定义
                if match := self.VAR_PATTERN.match(line):
                    var, op, value = match.groups()
                    value = value.strip()
                    
                    if op == '+=' and var in variables:
                        variables[var] += ' ' + value
                    else:
                        variables[var] = value
                    current_var = var
                # 处理续行
                elif current_var and self.CONTINUATION_PATTERN.search(line):
                    variables[current_var] += ' ' + line.strip('\\ ')
                else:
                    current_var = None
        
        return variables


def run_command(command: list, cwd: Optional[Path] = None, timeout: int = BUILD_TIMEOUT) -> bool:
    """运行命令并处理超时"""
    try:
        subprocess.run(command, cwd=cwd, check=True, timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Command timed out: {' '.join(command)}")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Command failed: {' '.join(command)}\nError: {e}")
        return False
        
def dump_json_file(data, file_path):
    """优化后的JSON文件写入"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def resolve_make_vars(vars: Dict[str, str], value: str) -> str:
    """解析Makefile变量引用"""
    patterns = [
        (re.compile(r'\$\(([^)]+)\)'), r'\1'),  # $(VAR)
        (re.compile(r'\${([^}]+)}'), r'\1')     # ${VAR}
    ]
    
    for pattern, group in patterns:
        while True:
            match = pattern.search(value)
            if not match:
                break
            var_name = match.group(1)
            var_value = vars.get(var_name, '')
            value = value.replace(match.group(0), var_value)
    
    return value.strip()

def collect_project_files(project_path: Path) -> Tuple[Set[Path], Set[Path]]:
    """收集项目源文件和头文件路径"""
    source_files = set()
    include_dirs = set()
    
    for root, _, files in os.walk(project_path):
        root_path = Path(root)

        if root_path.name in ("include", "lib"):
            include_dirs.add(root_path)

        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            full_path = os.path.join(root, file)
            
            if file_ext in ('.c', '.cpp', '.cc') and not any(excl in root for excl in EXCLUDED_DIRS):
                if 'test' not in file.lower():
                    source_files.add(full_path)
            elif file_ext in ('.h', '.hpp'):
                include_dirs.add(root)
    
    return source_files, include_dirs

def compile_to_ir(source_file: Path, output_dir: Path, 
                 include_dirs: Set[Path], flags: Dict[str, str]) -> Tuple[bool, str]:
    """编译单个文件到LLVM IR"""
    source_file = Path(source_file)
    compiler = 'clang++' if source_file.suffix in ('.cpp', '.cc') else 'clang'
    base_flags = ['-emit-llvm', '-S']
    
    # 构建基础命令
    cmd = [
        compiler,
        *base_flags,
        *shlex.split(flags.get('CPPFLAGS', '')),
        *shlex.split(flags.get('CXXFLAGS' if compiler == 'clang++' else 'CFLAGS', '')),
        str(source_file)
    ]
    
    # 添加包含路径
    for path in include_dirs:
        cmd.extend(['-I', str(path)])
    
    # 去除现有优化选项
    cmd = [arg for arg in cmd if arg not in OPTIMIZATION_LEVELS]
    
    success = True
    error_log = ""
    
    for opt_level in OPTIMIZATION_LEVELS:
        output_path = output_dir / opt_level / f"{source_file.stem}.ll"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.exists():
            continue
        
        final_cmd = cmd.copy()
        final_cmd.insert(1, opt_level)
        final_cmd.extend(['-o', str(output_path)])
        final_cmd_str = ' ' .join(final_cmd)
        try:
            result = subprocess.run(
                final_cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except subprocess.CalledProcessError as e:
            success = False
            error_log += f"Error compiling {source_file} with {opt_level}:\n{e.stderr}\n"
    
    return success, error_log

def process_project(project_path: str, output_path: str) -> bool:
    """处理整个项目"""
    output_path = Path(output_path)  # 转换为 Path 对象

    # 根据 log.txt 是否存在来判断该项目是否被处理过
    log_path = output_path / "log.txt"
    if log_path.exists():
        return True

    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Processing project: {Path(project_path).name}")
    
    project_path = Path(project_path)  # 将 project_path 也转换为 Path 对象
    
    # 生成构建系统
    if not (project_path / "Makefile").exists():
        configure_script = project_path / "configure"
        configure_ac = project_path / "configure.ac"
        
        # 如果只有 configure.ac，生成 configure 脚本
        if not configure_script.exists() and configure_ac.exists():
            logger.info(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Generating build system from configure.ac...")
            commands = [
                (["libtoolize", "--copy", "--force"], "libtoolize"),
                (["aclocal"], "aclocal"),
                (["autoheader"], "autoheader"),
                (["autoconf"], "autoconf"),
                (["automake", "--add-missing", "--copy"], "automake"),
            ]
            
            for cmd, name in commands:
                if not run_command(cmd, cwd=project_path):
                    logger.error(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Failed to run {name}")
                    return False
        
        # 运行 configure 脚本
        if configure_script.exists():
            logger.info(f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Running configure script...")
            if not run_command([str(configure_script), "--prefix=/tmp/build"], cwd=project_path):
                return False
        
        # 处理 CMake 项目
        cmake_file = project_path / "CMakeLists.txt"
        if cmake_file.exists():
            build_dir = project_path / "build"
            build_dir.mkdir(exist_ok=True)
            if not run_command(["cmake", ".."], cwd=build_dir):
                return False
    
    # 解析Makefile
    try:
        makefile = MakefileParser(project_path / "Makefile")
        flags = {
            var: resolve_make_vars(makefile.variables, makefile.variables.get(var, ""))
            for var in MAKEFILE_VARS
        }
    except FileNotFoundError:
        flags = {var: "" for var in MAKEFILE_VARS}
    
    # 收集文件
    source_files, include_dirs = collect_project_files(project_path)
    dump_json_file(list(source_files), os.path.join(output_path, "c_files.json"))

    if len(source_files) > 1500:
        logger.warning("[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] Project too large, skipping")
        return False
    
    # 处理文件
    failed_files = []
    all_errors = ""
    with tqdm(total=len(source_files), desc="Compiling files") as pbar:
        success_nums = 0
        for source_file in source_files:
            success, errors = compile_to_ir(
                source_file,
                output_path / "ir_files",
                include_dirs,
                flags
            )
            if success:
                success_nums += 1
            else:
                failed_files.append(str(source_file))
                all_errors += errors
            pbar.update(1)
    
    # 保存结果
    (output_path / "failed_list.json").write_text(json.dumps(failed_files))
    all_errors += f"\n\n success rate: {success_nums} / {len(source_files)}"
    log_path.write_text(all_errors)
    print(f"success rate: {success_nums} / {len(source_files)}\n")
    return len(failed_files) == 0

if __name__ == '__main__':
    
    # process_project(r'/home/lab314/cjw/ghcc/repos/repos1/akopytov_____sysbench', r"/home/lab314/cjw/similarity/datasets/source/source_lls/akopytov_____sysbench")
    repos_root = Path("/home/lab314/cjw/ghcc/repos/repos1")
    output_root = Path("/home/lab314/cjw/similarity/datasets/source/source_lls")
    error_log = Path("/home/lab314/cjw/similarity/desend2ir/error_pros.json")
    
    error_projects = []
    
    for project_dir in repos_root.iterdir():
        if not project_dir.is_dir():
            continue
        
        output_dir = output_root / project_dir.name
        if (output_dir / "log.txt").exists():
            logger.info(f"Skipping processed project: {project_dir.name}")
            continue
        
        try:
            success = process_project(project_dir, output_dir)
            if not success:
                error_projects.append(project_dir.name)
        except Exception as e:
            logger.error(f"Error processing {project_dir.name}: {str(e)}")
            error_projects.append(project_dir.name)
        
        # 实时保存错误日志
        error_log.write_text(json.dumps(error_projects))