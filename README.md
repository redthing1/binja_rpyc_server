
# rpyc server for binja

inspired by [binja-headless](https://github.com/hugsy/binja-headless)

example:
```py
import rpyc
c = rpyc.connect("127.0.0.1", 18812)
c.root
bn = c.root.binaryninja
bn.core_version()
```

sample binary loader:
```py
import rpyc
c = rpyc.connect("127.0.0.1", 18812)
bn = c.root.binaryninja
print(f"running on binaryninja {bn.core_version()}")

bin_file = "/bin/ls"
print(f"loading binary {bin_file}")
bv = bn.load(bin_file)
entry_fun = bv.entry_function
print(f"entry fun: {entry_fun} @ {entry_fun.start}")

# get text of hlil decompilation
def get_hlil_text(func):
    DisassemblySettings = bn.DisassemblySettings
    DisassemblyOption = bn.DisassemblyOption
    LinearViewObject = bn.lineardisassembly.LinearViewObject
    LinearViewCursor = bn.lineardisassembly.LinearViewCursor
    LinearDisassemblyLine = bn.lineardisassembly.LinearDisassemblyLine

    settings = DisassemblySettings()
    settings.set_option(DisassemblyOption.WaitForIL, True)

    lvo = LinearViewObject.single_function_hlil(func, settings)
    lines = []
    hlil_text = ""
    cursor = lvo.cursor
    while cursor.valid:
        lines.extend(cursor.lines)
        if not cursor.next(): break

    return hlil_text.strip()

print(f"decompiling...")
entry_fun_hlil = get_hlil_text(entry_fun)
print(f"entry func hlil:\n{entry_fun_hlil}")
```
