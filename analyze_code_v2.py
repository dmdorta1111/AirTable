import ast
import os

def analyze_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return

    issues = {
        "deep_nesting": [],
        "magic_numbers": []
    }

    class NestingVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_nesting = 0
            self.max_nesting = 0

        def visit_If(self, node):
            self.current_nesting += 1
            if self.current_nesting > 3:
                issues["deep_nesting"].append((node.lineno, f"Deeply nested condition (level {self.current_nesting})"))
            self.generic_visit(node)
            self.current_nesting -= 1

        def visit_For(self, node):
            self.current_nesting += 1
            self.generic_visit(node)
            self.current_nesting -= 1

        def visit_While(self, node):
            self.current_nesting += 1
            self.generic_visit(node)
            self.current_nesting -= 1

    visitor = NestingVisitor()
    visitor.visit(tree)

    # Magic numbers
    COMMON_NUMBERS = {0, 1, -1, 2, 10, 100, 1000, 24, 60, 3600, 0.5, 0.1}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if node.value not in COMMON_NUMBERS:
                # Check if it's part of an assignment to a named constant
                parent = None
                for p in ast.walk(tree):
                    if hasattr(p, 'body'):
                        if isinstance(p.body, list):
                            if node in p.body: parent = p; break
                    if hasattr(p, 'value') and p.value == node:
                        parent = p; break
                
                # Simple check: if it's in a comparison or as an argument, it might be a magic number
                # We'll just look for numbers in Compare or Call nodes
                pass

    return issues

# Let's search for magic numbers specifically in comparisons
def find_magic_numbers(tree, filepath):
    magic_numbers = []
    COMMON_NUMBERS = {0, 1, -1, 2, 10, 100, 1000, 24, 60, 3600, 0.5, 0.1, 8, 16, 32, 64, 128, 256, 512, 1024, 4096, 8192}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float)):
                    if comparator.value not in COMMON_NUMBERS:
                        magic_numbers.append((comparator.lineno, f"Magic number {comparator.value} in comparison"))
        if isinstance(node, ast.Call):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                    if arg.value not in COMMON_NUMBERS:
                        # Some numbers are okay in calls like round(x, 2)
                        if isinstance(node.func, ast.Name) and node.func.id == "round":
                            continue
                        magic_numbers.append((arg.lineno, f"Magic number {arg.value} in call to {ast.dump(node.func)}"))
    return magic_numbers

for root, dirs, files in os.walk('src/pybase'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    tree = ast.parse(f.read())
                    nesting_issues = []
                    
                    class NestingVisitor(ast.NodeVisitor):
                        def __init__(self):
                            self.current_nesting = 0
                        def visit_If(self, node):
                            self.current_nesting += 1
                            if self.current_nesting > 3:
                                nesting_issues.append((node.lineno, f"Deeply nested condition (level {self.current_nesting})"))
                            self.generic_visit(node)
                            self.current_nesting -= 1
                        def visit_For(self, node):
                            self.current_nesting += 1
                            self.generic_visit(node)
                            self.current_nesting -= 1
                    
                    visitor = NestingVisitor()
                    visitor.visit(tree)
                    
                    magic_nums = find_magic_numbers(tree, filepath)
                    
                    if nesting_issues or magic_nums:
                        print(f"FILE: {filepath}")
                        if nesting_issues:
                            print("  DEEP NESTING:")
                            for l, m in nesting_issues: print(f"    Line {l}: {m}")
                        if magic_nums:
                            print("  MAGIC NUMBERS:")
                            for l, m in magic_nums: print(f"    Line {l}: {m}")
                except SyntaxError:
                    continue
