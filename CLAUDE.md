# CLAUDE.md — 西方哲学研读 Wiki 项目章程

本文件**既是给 AI（你）的操作手册，也是项目自身的元规则定义**。修改本文件时请谨慎——它决定了整个知识库的结构与生长方式。

---

## 一、项目定位

本项目用 **LLM Wiki 模式**（Andrej Karpathy, 2026-04）对西方哲学进行系统化学习研究。核心思想：把零散的阅读、笔记、思考**预先编译**为一套互相链接、结构化、持续生长的 Markdown 私有维基，新知识回填形成复利。

适用 RAG 无法满足的"长效知识库 / 个人第二大脑"场景。

参考：[Karpathy 原 gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

---

## 二、目录结构

```
.
├── CLAUDE.md            ← 本文件：AI 工作手册 + Wiki 规范
├── README.md            ← 用户视角的项目说明
├── .gitignore           ← 忽略临时文件
│
├── raw/                 ← 原始资料（append-only，只增不改）
│   └── README.md        ← 原始资料的整理规范
│
├── wiki/                ← Wiki 主体（AI 维护，可演化）
│   ├── index.md         ← 总索引（每次 Ingest/Lint 后必须更新）
│   ├── graph.md         ← 知识图谱可视化页（vis-network）
│   ├── stylesheets/     ← MkDocs 自定义 CSS
│   ├── philosophers/    ← 哲学家页
│   ├── concepts/        ← 概念页
│   ├── works/           ← 著作页
│   ├── schools/         ← 学派页
│   ├── periods/         ← 时期页
│   ├── arguments/       ← 论证页
│   └── issues/          ← 议题/哲学问题页
│
├── templates/           ← 各类型页面的空白模板
│
├── hooks/               ← MkDocs 自定义钩子（构建时执行）
│   ├── __init__.py      ←   共享 STATE
│   ├── wikilinks.py     ←   [[X]] 解析 + 待创建徽章
│   ├── backlinks.py     ←   反链面板注入
│   └── graph.py         ←   写 site/assets/graph.json
│
├── mkdocs.yml           ← MkDocs 站点配置
├── requirements.txt     ← Python 依赖（mkdocs + mkdocs-material）
│
└── meta/                ← 项目元数据（不属于 Wiki 主体）
    ├── methodology.md   ← LLM Wiki 模式说明
    ├── glossary.md      ← 核心术语统一表
    ├── progress.md      ← 研读进度看板
    └── reading-list.md  ← 延伸阅读书单（按主题组织的待读/已读书目）

构建产物 `site/` 目录在 .gitignore 中（部署时通过 `mkdocs gh-deploy` 推到 gh-pages 分支）。
```

---

## 三、命名约定

- **页面文件名** = 该实体最常用的中文译名（西方哲学以中文译名为准）。  
  例：`柏拉图.md`、`理念论.md`、`理想国.md`
- **链接语法**：`[[页面名]]`（默认显示名）或 `[[页面名|显示文本]]`（自定义显示）
- **首次出现**时使用全称；后续可使用简称；但**链接必须指向准确页面名**
- **避免一词多义**：如确实存在重名（少见），在页面名前加限定词，例如 `柏拉图的理念论` vs `亚里士多德的实体`
- **大小写**：文件名使用中文，全程不混用大小写

---

## 四、Wiki 页面类型与模板

见 `templates/` 目录。每类页面有固定结构，**新增/重写页面必须基于对应模板**。允许增删内容，但**头部 frontmatter 和基本骨架不能改**。

| 类型 | 模板 | 何时创建 |
|------|------|----------|
| 哲学家 | `template-philosopher.md` | 任何进入研读视野的哲学家 |
| 概念 | `template-concept.md` | 重要的哲学概念、术语、学说 |
| 著作 | `template-work.md` | 重要哲学著作 |
| 学派 | `template-school.md` | 哲学流派、传统 |
| 时期 | `template-period.md` | 哲学史分期 |
| 论证 | `template-argument.md` | 经典的哲学论证 |
| 议题 | `template-issue.md` | 持续讨论的哲学问题 |

每种类型页面 frontmatter 中含 `status` 字段：`stub`（初稿）→ `active`（充实中）→ `mature`（稳定）。

---

## 五、双向链接规则

1. **创建页面时**：在"相关条目"区添加所有相关页面的 `[[链接]]`（正向链接）
2. **维护时**：每当某个页面提到另一个实体，必须建立链接
3. **Lint 时**：检查反向链接 —— 任何被 `[[]]` 引用的目标页面，必须在引用方页面的"相关条目"区列出引用方（用 grep 反向检索）
4. **链接要"宁滥勿缺"**：知识图谱的价值在于连接密度

---

## 六、三大工作流

### 6.1 Ingest（摄入 / 编译）

**触发**：用户提供了新原始资料（笔记、书摘、读后感、PDF 摘录、对话等）。

**流程**：
1. 将原始材料以 Markdown 形式放入 `raw/<YYYY-MM-DD>-<主题>.md`（参见 `raw/README.md`）
2. **提炼**：识别资料中的**哲学家、概念、著作、学派、时期、论证、议题**
3. **查重**：在 `wiki/` 中查找是否已存在对应页面（用 grep 或 Glob）
4. **不存在** → 基于对应模板创建新页面，正向链接到已存在的相关页面
5. **已存在** → 增量更新：补充新材料、修正过时信息、在"补充资料"区追加来源链接
6. **更新 `wiki/index.md`**：把新页面加入对应分类的索引列表
7. **报告**：向用户简明列出"本次新增/更新了哪些页面"以及理由

### 6.2 Query（查询）

**触发**：用户提问或请求梳理某个问题。

**流程**：
1. 先用 grep/Glob 在 `wiki/` 中检索相关页面
2. 读取相关页面，组装回答
3. **优先基于 Wiki 已有内容**；不要凭空捏造
4. **如果 Wiki 内容不足**：明确告诉用户"该问题 Wiki 中暂未覆盖"，建议补充哪类原始资料
5. **如果产生新结论**（用户确认有价值的新理解）：通过 Ingest 工作流回写入 Wiki

### 6.3 Lint（巡检）

**触发**：用户主动要求 / 项目积累一段时间后 / 重大修订前。

**流程**：
1. **孤立页面检查**：`grep -L '\[\[' wiki/**/*.md` → 找出无任何链接的页面
2. **死链检查**：`[[xxx]]` 中指向不存在的页面 → 删除或创建
3. **反向链接补全**：每个被引用的页面，应在"相关条目"区反向列出引用方
4. **冲突信息检查**：同一概念在不同页面的表述是否一致
5. **过时内容标记**：标注 Wiki 中已知的局限和待补充之处
6. **索引更新**：`wiki/index.md` 与实际页面是否一致
7. **报告**：以清单形式输出问题与建议修复方案（**默认不自动修改，等待用户确认**）

---

## 七、质量标准

- **引用**：每个事实性陈述应标注出处（原始资料路径或经典文献卷章节号）
- **区分**：明确区分"该哲学家本人的观点"vs"后世解读"vs"AI 总结"
- **不确定**：标注存疑/争议处（如 `⚠️ 待考证`）
- **不要**：凭空填补无来源的内容；遇到空白应明确说"暂无资料"
- **术语**：使用 `meta/glossary.md` 中约定的中文译名
- **简洁**：页面应是知识浓缩，不是论文；冗长内容拆分为子页

### 7.1 资料来源类型标注（source_type）

为清晰区分资料的可信度层级，所有 Wiki 页面的 frontmatter 必须包含 `sources` 字段，按 `primary / secondary / ai_summary` 三类标注来源：

```yaml
sources:
  - file: raw/2026-08-XX-理想国读书笔记.md
    type: primary        # 原始文献（最高优先级）
    citation: "卷七 514a-517c"
  - file: raw/2026-08-XX-苏菲的世界笔记.md
    type: secondary      # 后世解读（中等优先级）
    citation: "Gaarder 1991, 第N章"
  - type: ai_summary     # AI 综合推论（最低优先级）
    note: "根据已有 primary/secondary 推导"
```

| 类型 | 说明 | 可信度 |
|------|------|--------|
| `primary` | 原始文献（柏拉图对话录、西塞罗著作、康德三大批判等） | 最高 |
| `secondary` | 后世解读（研究专著、《苏菲的世界》、维基百科、教科书） | 中等 |
| `ai_summary` | AI 综合推论（无具体来源支撑的总结） | 最低 |

**规则**：
- 页面正文优先追溯 primary source；用 secondary 时须明确标注。
- 同一论断有多源时，按类型优先级排序引用。
- 普及性读物（如《苏菲的世界》）覆盖广但深度浅，可用作 survey / 导航工具 —— 用户据此创建 stub 后，再决定是否回到原始文献（primary）填充。

---

## 八、与用户的协作约定

- **提炼后必须报告**：本次操作产生了什么、修改了什么、为什么
- **不要自动删除**：用户写的笔记、原始资料即便显得冗余也保留
- **大改前先确认**：涉及页面结构、模板规范、命名约定的修改，需先和用户对齐
- **Lint 默认只报告不修改**：除非用户明确说"直接修"
- **不要静默做大事**：Ingest 多份资料时，每份单独报告；不要一次生成大量页面让用户难以审核

---

## 九、常用命令

```bash
# 查找所有 Wiki 页面
find wiki -name "*.md" -type f

# 列出所有出站链接
grep -rhoE '\[\[[^]]+\]\]' wiki/ | sort -u

# 查找孤立页面（无任何出站链接）
grep -L '\[\[' $(find wiki -name "*.md")

# 查找死链（指向不存在的页面）
for link in $(grep -rhoE '\[\[[^]]+\]\]' wiki/ | sed 's/\[\[//;s/\]\]//' | sort -u); do
  name="${link%%|*}"
  [ -f "wiki/$name.md" ] || [ -f "wiki/philosophers/$name.md" ] || echo "死链: $name"
done

# 站点构建 / 预览 / 部署（需要先激活 venv：source .venv/bin/activate）
mkdocs serve                                          # 本地预览 http://127.0.0.1:8000
mkdocs build --strict                                 # 全站构建 + 断链检查
mkdocs gh-deploy --force                              # 部署到 GitHub Pages（推到 gh-pages 分支）
```

---

## 十、当前项目阶段

> 起步期：刚搭建骨架，Wiki 主体为空。下一步是与用户确认第一个切入点和第一批资料。

参见 `meta/progress.md`。

---

## 十一、静态站点发布（MkDocs + Material → GitHub Pages）

本项目通过 [MkDocs](https://www.mkdocs.org/) + [Material](https://squidfunk.github.io/mkdocs-material/) 主题构建静态站点，托管在 GitHub Pages。

### 站点地址

`https://vidazhou.github.io/philosophy-wiki/`

### 三大自定义功能（由 `hooks/` 实现）

- **`hooks/wikilinks.py`** —— 构建时扫描每页 Markdown，将 `[[X]]` 和 `[[X|Y]]` 解析为：
  - 目标存在 → 真正的 `<a href>` 链接
  - 目标不存在 → `<span class="wikilink-stub">` "待创建" 样式（CSS 在 `wiki/stylesheets/extra.css`）
- **`hooks/backlinks.py`** —— 每页渲染后，在末尾自动追加 `<aside class="backlinks">` "被引用于" 面板，列出所有反向链接
- **`hooks/graph.py`** —— 构建结束（`on_post_build`）时，写出 `site/assets/graph.json`（含 nodes + edges），由 `wiki/graph.md` 用 [vis-network](https://visjs.github.io/vis-network/) 渲染

### 站点内容来源

- `mkdocs.yml` 的 `docs_dir: wiki` 让 MkDocs 直接读 `wiki/` 目录（**不动 wiki 内容**）
- `wiki/graph.md` 是知识图谱可视化页（vis-network 通过 CDN 加载）
- `wiki/stylesheets/extra.css` 自定义反链面板、stub 链接、知识图谱容器的样式

### 工作流

```bash
cd /Users/vidazhou/西方哲学研读
source .venv/bin/activate        # 激活 venv

mkdocs serve                     # 本地预览：http://127.0.0.1:8000
mkdocs build --strict            # 全站构建（含断链检查）
mkdocs gh-deploy --force         # 部署到 GitHub Pages
```

### 注意事项

- **URL 路径**：因部署在 GitHub Pages 子路径下，生成 HTML 中的链接是相对路径；本地预览用 `mkdocs serve` 测试
- **frontmatter 中的 `[[链接]]`**：hooks 会跳过 YAML 块（用 `split("---", 2)` 分离），但 body 内会替换
- **forward link**（指向不存在页面的 `[[X]]`）会显示为虚线下划线 + 紫色"待创建"徽章
- **构建产物 `site/`** 在 .gitignore 中；部署通过 `mkdocs gh-deploy` 推到 `gh-pages` 分支
- **GitHub Pages 设置**：Settings → Pages → Build & deployment → Branch = `gh-pages` / `/ (root)`

### 日常维护要点

- 修改 `wiki/` 内容后，执行 `mkdocs gh-deploy --force` 即可
- 修改 `hooks/` 后，必须重新 build（不要假设 dev server 自动刷新 hook 代码）
- 私有仓库 + GitHub Pages 需要 GitHub Pro；公开访问仅限已登录用户
- 如新增分类目录，记得在 `wiki/<新目录>/index.md` 放一个一行标题文件，让 Material 的 `navigation.indexes` 渲染出分类入口