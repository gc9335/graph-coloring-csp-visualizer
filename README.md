# 图着色 CSP 六版本动态实验台

这是一个可直接部署到 GitHub Pages 的纯静态网页项目。

## 静态文件

- `index.html`
- `styles.css`
- `app.js`
- `solver.js`
- `.nojekyll`

## GitHub Pages 部署

1. 把以上静态文件推送到仓库。
2. 进入 GitHub 仓库的 `Settings -> Pages`。
3. 选择发布来源：
   - `Deploy from a branch`
   - 分支选择 `main`
   - 文件夹选择 `/ (root)`
4. 保存后等待 GitHub Pages 完成发布。

## 本地验证

- 算法测试：`node tests/solver.test.mjs`
- 直接本地开静态服务即可访问，例如：`python -m http.server`
