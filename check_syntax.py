import sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        compile(f.read(), sys.argv[1], 'exec')
    print("Syntax OK")
except SyntaxError as e:
    print(f"SyntaxError: {e.msg} at line {e.lineno}, offset {e.offset}")
    if e.text:
        print(f"Line content: {repr(e.text)}")
except Exception as e:
    print(f"Error: {e}")
