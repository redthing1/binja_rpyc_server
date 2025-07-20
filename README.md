
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
