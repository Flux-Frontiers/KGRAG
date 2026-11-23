# Release Notes -- v0.19.0

> Released: 2026-11-22

kg-rag can now draw. `kgrag imagine` renders an image from a prompt, or from
passages it retrieves across your registered knowledge graphs, and a new MCP
tool gives an agent the same ability. Nothing about federation, the registry
or the existing commands changes.

## What changed

**Images from a prompt or from retrieved passages.** `kgrag imagine "a
lighthouse at dusk"` renders the prompt as typed. `kgrag imagine --query "the
great fire of London" --kind diary` retrieves passages, has a text model
rewrite them into one scene, and renders that. Passages from documents, books
and diaries are rewritten as historical scenes; hits from code, memory and
other non-prose graphs are rewritten as technical illustrations.
`--context-only` shows the passages and the prompt without rendering, and
`--no-rewrite` sends the passages as they are.

**Four ways to render.** The image client is
[imagewright](https://github.com/Flux-Frontiers/imagewright), so kg-rag needs
no gutenberg_kg. It uses an image server (`--endpoint`, `IMAGE_ENDPOINT`, or
one it finds on localhost), FLUX.2 Klein loaded in the same process with no
server running, a LAN worker (`--worker`), or OpenAI. When no server answers
and the local extra is installed, it loads FLUX in process and says so first.
When nothing is available, it lists the ways to fix that.

**An MCP tool.** `kg_imagine` does the same for an agent and returns the image
to the MCP client, compressed under the client's size limit. `kgrag-mcp` starts
and lists its other tools without the image extra.

**The KGRAG owl.** The dashboard's Synthesize tab shows an owl that tracks the
pipeline: waiting, walking the graphs, answering, done, with how many snippets
and graphs ground the answer.

**A new logo and a refreshed README.** The federation fan replaces the brain,
in the fleet's Art Techno style. The README covers every implemented backend
and command, gains a What's new section, and its images now show on PyPI.

## Upgrading

`pip install -U "kg-rag[imagine]"` adds image generation; add `imagine-local`
for in-process FLUX on Apple Silicon (`pip install -U
"kg-rag[imagine,imagine-local]"`). `kg-rag[all]` includes `imagine` but not
`imagine-local`. The query rewrite uses the text model that `SYNTH_BACKEND`,
`SYNTH_ENDPOINT` and `SYNTH_MODEL` configure. No registry or index changes.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
