# KGRAG CLI Reference

## Command Summary

| Command | Purpose |
|---------|---------|
| `kgrag query` | Cross-KG semantic search |
| `kgrag pack` | Extract code snippets with context |
| `kgrag list` | List all registered KGs |
| `kgrag status` | Show registry health |
| `kgrag init` | Initialize and register KGs in a repo |
| `kgrag register` | Manually register a KG |
| `kgrag unregister` | Remove a KG from registry |
| `kgrag scan` | Discover unregistered KGs |
| `kgrag analyze` | Cross-KG statistics |
| `kgrag info` | Detailed info about a KG |
| `kgrag mcp` | Launch MCP server |

## Detailed Command Options

### query
```
kgrag query <query-text> [OPTIONS]

Options:
  -k INTEGER              Number of results per KG [default: 8]
  --kind [code|doc|meta]  Filter by KG kind
  --json                  Output as JSON
  --registry PATH         Override registry path
```

### pack
```
kgrag pack <query-text> [OPTIONS]

Options:
  -k INTEGER              Number of results per KG [default: 8]
  --context INTEGER       Lines of context around snippets [default: 5]
  --kind [code|doc|meta]  Filter by KG kind
  --out FILE              Write to file instead of stdout
  --registry PATH         Override registry path
```

### list
```
kgrag list [OPTIONS]

Options:
  --kind [code|doc|meta]  Filter by KG kind (code/doc/meta)
  --registry PATH         Override registry path
```

### init
```
kgrag init <path> [OPTIONS]

Options:
  --name TEXT             Custom name for the KG
  --layer TEXT            Specify layers (code, doc) - can be repeated
  --wipe                  Rebuild existing KGs
  --registry PATH         Override registry path
```

### status
```
kgrag status [OPTIONS]

Options:
  --registry PATH         Override registry path
```

Shows:
- Total number of registered KGs broken down by kind
- Built/unbuilt status for each
- Any missing or invalid paths
