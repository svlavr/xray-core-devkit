# Third-party tools and services

The toolkit adapters do not relicense the servers, CLIs, models or services they
connect to. Dependency metadata fixes the working arrangement; users obtain the
actual components from the original distributions. Keep their notices when
redistributing their code or binaries.

- **gopls v0.23.0**, Go tools: BSD-style license. The adapter is deliberately
  tied to this version's reference output.
  [Source license](https://github.com/golang/tools/blob/gopls/v0.23.0/LICENSE).
- **deadcode**, Go tools v0.50.0: BSD-style license.
  [Source license](https://github.com/golang/tools/blob/v0.50.0/LICENSE).
- **GitNexus 1.6.12:** PolyForm Noncommercial 1.0.0. Its permitted-purpose and
  notice requirements remain applicable, including when installed separately.
  Required Notice: Copyright Abhigyan Patwari (https://github.com/abhigyanpatwari/GitNexus)
  [Exact release license](https://github.com/abhigyanpatwari/GitNexus/blob/v1.6.12/LICENSE).
- **Repomix 1.18.1:** MIT. [Repository](https://github.com/yamadashy/repomix).
- **ast-grep CLI 0.45.3:** MIT. [Repository](https://github.com/ast-grep/ast-grep).
- **Gas City v1.5.0:** MIT.
  [Exact release license](https://github.com/gastownhall/gascity/blob/v1.5.0/LICENSE).
- **Beads v1.3.1:** MIT.
  [Exact release license](https://github.com/gastownhall/beads/blob/v1.3.1/LICENSE).
- **Dolt v2.4.2:** Apache-2.0.
  [Exact release license](https://github.com/dolthub/dolt/blob/v2.4.2/LICENSE).
- **Codex rust-v0.162.0-alpha.2:** Apache-2.0, with upstream NOTICE.
  [License](https://github.com/openai/codex/blob/rust-v0.162.0-alpha.2/LICENSE),
  [NOTICE](https://github.com/openai/codex/blob/rust-v0.162.0-alpha.2/NOTICE).
- **Gas City roles pack:** imported by its public repository and exact recorded
  ref, not vendored here. This is a separate repository; verify its applicable
  terms before use or redistribution rather than applying the runtime's MIT
  license to it automatically.
- **Context7:** separately operated remote MCP service.
  [Public service](https://context7.com/). Its access and service terms are
  independent of this toolkit's source license.

The npm package locks include transitive dependency metadata and integrity
values. Consult each installed package's own license and notices; the names
above do not assert one license for the entire transitive tree. Go, Node and
the user's Codex/model access are separately installed prerequisites.


## Public code search

**grep.app:** separately operated remote MCP service at
`https://mcp.grep.app`, used through the allowlisted `searchGitHub` tool.
[Service announcement](https://vercel.com/blog/grep-a-million-github-repositories-via-mcp).
Only public queries are permitted. No service source or binary is redistributed;
service access and terms remain independent of the toolkit's MPL-2.0 license.
Search-result code retains its original project's license and notices. Inspect
the exact source and applicable terms before reuse.

## Workflow responsibility references

The solution-research, feature-delivery and focused review instructions adapt
responsibilities from the following public sources, without importing their full
frameworks, execution policies or project contracts:

- **ECC**, search-first workflow (MIT):
  [source revision](https://github.com/affaan-m/ECC/blob/76aaa77df6adc5b889e689007bf99b9a4f74af34/skills/search-first/SKILL.md).
- **Get Shit Done**, phase researcher and verifier (MIT):
  [source revision](https://github.com/gsd-build/get-shit-done/tree/bdcaab2c752d9a33a1a1ca9acf3a3c81fb991815/agents).
- **BMAD**, verification-gap review (MIT):
  [source revision](https://github.com/bmad-code-org/BMAD-METHOD/blob/8f0d50e1817fdd8fcf05a20c524218222d13cd8d/skills/bmad-build/review-prompts/verification-gap.md).
- **Superpowers**, brainstorming and writing plans (MIT):
  [source revision](https://github.com/obra/superpowers/tree/bb92a77741419a4ab5f06e711a283343f1ada0c3/skills).
- **Anthropic code-simplifier** (Apache-2.0):
  [source revision](https://github.com/anthropics/claude-plugins-official/blob/ea10b213686c90bb1984b2016937310e05336cf3/plugins/code-simplifier/agents/code-simplifier.md).

These are design references for independently maintained instructions. Their
licenses and any required upstream notices remain applicable to code or text
copied from them; this distribution does not relicense those projects.
