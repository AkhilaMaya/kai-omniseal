import ast
import re
import time
import unicodedata
import threading
from collections import Counter
from flask import Flask

# Adjust these as needed for your environment
MAX_CODE_SIZE = 50000      # 50KB
MAX_VALIDATION_TIME = 1.5  # seconds
MAX_AST_NODES = 2500
MAX_LINE_LENGTH = 500
MAX_NESTED_DEPTH = 8

def validate_code_integrity(context: str) -> bool:
    """
    Validates code integrity with comprehensive security checks.
    Returns False if any security issues detected, True if safe.
    """
    if context is None or not isinstance(context, str):
        print("Code integrity check failed: Empty or invalid context")
        return False

    validation_completed = False
    validation_result = False

    def validation_worker():
        nonlocal validation_completed, validation_result
        try:
            validation_result = _perform_validation(context)
        except Exception as e:
            print(f"Validation worker exception: {str(e)}")
            validation_result = False
        finally:
            validation_completed = True

    def _perform_validation(code_str: str) -> bool:
        # Normalize unicode
        try:
            normalized_code = unicodedata.normalize('NFKC', code_str)
        except Exception as e:
            print(f"Code integrity check failed: Unicode normalization error: {str(e)}")
            return False

        # Homoglyph detection
        for char in normalized_code:
            if ord(char) > 127 and char not in '§£€¥©®™':
                cat = unicodedata.category(char)
                if cat not in ('Lu','Ll','Lt','Lm','Lo','Nd','Nl','No','Pc','Pd','Ps','Pe','Pi','Pf','Po'):
                    print(f"Code integrity check failed: Suspicious Unicode char: {char} (U+{ord(char):04X})")
                    return False

        if len(normalized_code) == 0:
            print("Code integrity check failed: Empty code")
            return False
        if len(normalized_code) > MAX_CODE_SIZE:
            print(f"Code integrity check failed: Size limit exceeded ({len(normalized_code)} > {MAX_CODE_SIZE})")
            return False

        # Long line check
        for idx, line in enumerate(normalized_code.splitlines(), 1):
            if len(line) > MAX_LINE_LENGTH:
                print(f"Code integrity check failed: Line {idx} exceeds max length ({len(line)})")
                return False

        # Obfuscation patterns & whitespace
        def regex_with_timeout(pattern, text, timeout=0.5):
            result = []
            regex_thread = threading.Thread(target=lambda: result.extend(re.findall(pattern, text)))
            regex_thread.daemon = True
            regex_thread.start()
            regex_thread.join(timeout)
            if regex_thread.is_alive():
                raise TimeoutError("Regex pattern matching timed out")
            return result

        try:
            pattern_counts = Counter(regex_with_timeout(r'(.{10,}?)\1{2,}', normalized_code))
            if pattern_counts:
                most_common = pattern_counts.most_common(1)[0]
                print(f"Code integrity check failed: Repetitive pattern detected ({most_common[1]} times)")
                return False
            if len(re.findall(r'\s{10,}', normalized_code)) > 0:
                print("Code integrity check failed: Excessive whitespace detected")
                return False
            obfuscation_patterns = [
                r'\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}',
                r'\\u[0-9a-fA-F]{4}\\u[0-9a-fA-F]{4}',
                r'_(.)_\s*\s*["\'](.*?)["\']\s*',
                r'chr\s*\s*\d+\s*\s*\+\s*chr\s*\s*\d+\s*',
                r'exec\s*\s*compile\s*',
                r'exec\s*\s*["\'](.?)["\']\s\.join',
                r'exec\s*\s*bytes\.fromhex',
                r'eval\s*\s*["\'](.?)["\']\s\.join',
                r'exec\s*\s*["\'](.?)["\']\s\.encode\s*\s*["\'](.?)["\']\s*\.decode\s*\s["\'](.*?)["\']\s*',
                r'(?:globals|locals)\s*\s*\s*\s*["\'](.*?)["\']\s*'
            ]
            for pattern in obfuscation_patterns:
                if regex_with_timeout(pattern, normalized_code):
                    print(f"Code integrity check failed: Obfuscation pattern detected: {pattern}")
                    return False
        except TimeoutError:
            print("Code integrity check failed: Regex pattern matching timed out - possible ReDoS attack")
            return False
        except Exception as e:
            print(f"Code integrity check failed: Pattern detection error: {str(e)}")
            return False

        # Python code heuristic
        python_indicators = ['def ', 'class ', 'import ', 'from ', '=', 'print(', 'if ', 'for ', 'while ']
        if not any(ind in normalized_code for ind in python_indicators):
            print("Code integrity check failed: Does not appear to be Python code")
            return False

        # AST analysis
        try:
            ast_tree = ast.parse(normalized_code)
        except SyntaxError as e:
            print(f"Code integrity check failed: Syntax error at line {e.lineno}, col {e.offset}: {e.text}")
            return False
        except Exception as e:
            print(f"Code integrity check failed: AST parsing error: {str(e)}")
            return False

        ast_node_count = sum(1 for _ in ast.walk(ast_tree))
        if ast_node_count > MAX_AST_NODES:
            print(f"Code integrity check failed: AST too complex ({ast_node_count} nodes > {MAX_AST_NODES})")
            return False

        dangerous_functions = {
            'exec', 'eval', 'compile', 'system', 'popen', 'subprocess', 'os.system', 'os.popen',
            'os.spawn', 'pty.spawn', 'platform._syscmd_uname', 'os.execl', 'os.execle', 'os.execlp',
            'os.execv', 'os.execve', 'os.execvp', 'os.execvpe', 'os.spawnl', 'os.spawnle', 'os.spawnlp',
            'os.spawnv', 'os.spawnve', 'os.spawnvp', 'os.spawnvpe', 'posix.system', 'posix.popen',
            'platform.popen', 'subprocess.call', 'subprocess.check_call', 'subprocess.check_output', 'subprocess.run', 'subprocess.Popen',
            'globals', 'locals', 'vars', 'getattr', 'setattr', 'delattr', 'hasattr', 'type', 'memoryview',
            'staticmethod', 'classmethod', 'super', 'open', 'file', 'fileinput.input', 'io.open',
            'io.FileIO', 'io.BytesIO', 'io.StringIO', 'io.TextIOWrapper', 'codecs.open', 'builtins.open', 'pathlib.Path.open',
            'socket.socket', 'ssl.wrap_socket', 'urllib.request.urlopen', 'urllib.request.Request',
            'http.client.HTTPConnection', 'ftplib.FTP', 'smtplib.SMTP', 'telnetlib.Telnet', 'xmlrpc.client.ServerProxy',
            'import', 'importlib', 'importlib.import_module', '_import_', 'load_module',
            'pickle.loads', 'pickle.load', 'marshal.loads', 'marshal.load', 'cPickle.loads', 'cPickle.load',
            'shelve.open', 'json.loads', 'yaml.load', 'yaml.safe_load',
            'multiprocessing.Process', 'threading.Thread', 'concurrent.futures.ProcessPoolExecutor',
            'concurrent.futures.ThreadPoolExecutor', 'ctypes', 'cffi', 'mmap',
            'functools.partial', 'shutil.rmtree', 'atexit.register'
        }
        dangerous_attributes = {
            '_code', 'closure', 'dict', 'class', 'bases', 'subclasses', 'mro_',
            '_qualname', 'module', 'name', 'package', 'builtins', 'globals_',
            '_annotations', 'defaults', 'self', 'func', 'get', 'set', 'delete_',
            '_getattr', 'setattr', 'delattr', 'getattribute', 'reduce', 'reduce_ex_',
            '_dir', 'repr', 'str', 'bytes', 'file', 'path', 'loader', 'spec_',
            'protected', '_private', '_mangled'
        }
        class SecurityVisitor(ast.NodeVisitor):
            def _init_(self):
                self.dangerous_calls = set()
                self.dangerous_attrs = set()
                self.current_depth = 0
                self.max_depth = 0
                self.import_names = set()
                self.has_star_import = False
            def generic_visit(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                super().generic_visit(node)
                self.current_depth -= 1
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in dangerous_functions:
                        self.dangerous_calls.add(func_name)
                elif isinstance(node.func, ast.Attribute):
                    attr_path = []
                    current = node.func
                    while isinstance(current, ast.Attribute):
                        attr_path.append(current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        attr_path.append(current.id)
                    attr_path.reverse()
                    full_path = '.'.join(attr_path)
                    if any(dangerous in full_path for dangerous in dangerous_functions):
                        self.dangerous_calls.add(full_path)
                self.generic_visit(node)
            def visit_Attribute(self, node):
                if hasattr(node, 'attr') and node.attr in dangerous_attributes:
                    self.dangerous_attrs.add(node.attr)
                self.generic_visit(node)
            def visit_Import(self, node):
                for name in node.names:
                    self.import_names.add(name.name.split('.')[0])
                self.generic_visit(node)
            def visit_ImportFrom(self, node):
                if node.module:
                    self.import_names.add(node.module.split('.')[0])
                for name in node.names:
                    if name.name == '*':
                        self.has_star_import = True
                self.generic_visit(node)
        visitor = SecurityVisitor()
        visitor.visit(ast_tree)
        if visitor.dangerous_calls:
            print(f"Code integrity check failed: Dangerous function calls detected: {', '.join(visitor.dangerous_calls)}")
            return False
        if visitor.dangerous_attrs:
            print(f"Code integrity check failed: Dangerous attribute access detected: {', '.join(visitor.dangerous_attrs)}")
            return False
        if visitor.max_depth > MAX_NESTED_DEPTH:
            print(f"Code integrity check failed: Excessive nesting depth ({visitor.max_depth} > {MAX_NESTED_DEPTH})")
            return False
        dangerous_imports = {
            'os', 'sys', 'subprocess', 'shutil', 'ctypes', 'pickle', 'cPickle', 'marshal',
            'shelve', 'tempfile', 'glob', 'builtins', '_frozen_importlib', 'importlib',
            'imp', 'pty', 'platform', 'posix', 'pwd', 'grp', 'fcntl', 'pipes', 'signal',
            'pathlib', 'socket', 'http', 'urllib', 'xmlrpc', 'ftplib', 'smtplib', 'telnetlib',
            'socketserver', 'asyncio', 'multiprocessing', 'mmap', 'resource', 'nis', 'spwd',
            'termios', 'tty', 'gc', 'sysconfig', '_sitebuiltins', 'site', '_io', '_socket',
            'distutils', 'setuptools', 'code', 'commands', 'pdb', 'profile', 'trace', 'runpy'
        }
        suspicious_imports = visitor.import_names.intersection(dangerous_imports)
        if suspicious_imports:
            print(f"Code integrity check failed: Dangerous modules imported: {', '.join(suspicious_imports)}")
            return False
        if visitor.has_star_import:
            print("Code integrity check failed: Star imports are forbidden (from x import *)")
            return False
        if '_' in normalized_code and ('import' in normalized_code or 'builtins_' in normalized_code):
            print("Code integrity check failed: Potential use of dunder methods for sandbox escape")
            return False
        # Weird byte sequences
        byte_sequence_patterns = [
            rb'\x00\x00\x00\x00',  # Null bytes
            rb'\xca\xfe\xba\xbe',  # Java class
            rb'\xcf\xfa\xed\xfe',  # Mach-O binary
            rb'\x7fELF',           # ELF binary
            rb'MZ',                # Windows exe
            rb'\x4d\x5a'
        ]
        code_bytes = normalized_code.encode('utf-8', errors='ignore')
        for pattern in byte_sequence_patterns:
            if pattern in code_bytes:
                print("Code integrity check failed: Suspicious byte sequence detected")
                return False
        return True

    # Start the validation thread with timeout
    validation_thread = threading.Thread(target=validation_worker)
    validation_thread.daemon = True
    validation_thread.start()
    validation_thread.join(MAX_VALIDATION_TIME)
    if not validation_completed:
        print("Code integrity check failed: Validation timed out")
        return False
    return validation_result

app = Flask(__name__)

def run_main_logic():
    # You can trigger your validation function or other logic here
    print("Kai Omniseal is online. Awaiting commands.")

@app.route('/')
def home():
    return "Kai Omniseal is alive and listening."

if _name_ == '_main_':
    threading.Thread(target=run_main_logic).start()
    app.run(host='0.0.0.0', port=8080)
