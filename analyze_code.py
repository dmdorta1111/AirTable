import ast
import os

def analyze_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return

    issues = {
        "missing_return_type": [],
        "missing_param_type": [],
        "any_type": [],
        "long_functions": [],
        "large_classes": [],
        "deep_nesting": [],
        "missing_docstring": [],
        "magic_numbers": []
    }

    # Module docstring
    if not ast.get_docstring(tree):
        issues["missing_docstring"].append((0, "Module missing docstring"))

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Type hints
            if node.returns is None and node.name != "__init__":
                issues["missing_return_type"].append((node.lineno, f"Function '{node.name}' missing return type"))
            
            for arg in node.args.args:
                if arg.annotation is None and arg.arg != "self" and arg.arg != "cls":
                    issues["missing_param_type"].append((node.lineno, f"Argument '{arg.arg}' in '{node.name}' missing type hint"))

            # Long functions
            length = node.end_lineno - node.lineno
            if length > 50:
                issues["long_functions"].append((node.lineno, f"Function '{node.name}' is too long ({length} lines)"))

            # Missing docstring
            if not ast.get_docstring(node):
                issues["missing_docstring"].append((node.lineno, f"Function '{node.name}' missing docstring"))

            # Deep nesting
            nesting_level = 0
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    # This is a bit simplistic, but good enough for a start
                    pass

        if isinstance(node, ast.ClassDef):
            # Large classes
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if len(methods) > 20:
                issues["large_classes"].append((node.lineno, f"Class '{node.name}' has too many methods ({len(methods)})"))
            
            # Missing docstring
            if not ast.get_docstring(node):
                issues["missing_docstring"].append((node.lineno, f"Class '{node.name}' missing docstring"))

    return issues

for root, dirs, files in os.walk('src/pybase'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            issues = analyze_file(filepath)
            if any(issues.values()):
                print(f"FILE: {filepath}")
                for category, category_issues in issues.items():
                    if category_issues:
                        print(f"  {category.upper()}:")
                        for line, msg in category_issues:
                            print(f"    Line {line}: {msg}")
