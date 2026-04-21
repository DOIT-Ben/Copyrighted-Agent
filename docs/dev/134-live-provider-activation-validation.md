# 真实 Provider 激活验证记录
## 日期

- 2026-04-21

## 输入

- 上游基础地址：`https://api.minimaxi.com/v1`
- 上游模型：`MiniMax-M2.7-highspeed`
- API Key 环境变量名：`MINIMAX_API_KEY`

## 执行动作

1. 保持 `config/local.json` 继续指向本地桥接入口 `http://127.0.0.1:18011/review`。
2. 在联调命令进程内注入 `MINIMAX_API_KEY`。
3. 启动 `scripts/start_real_bridge.ps1`。
4. 运行 `py -m app.tools.release_validation --config config\local.json --json`。
5. 运行 `py -m app.tools.delivery_closeout --config config\local.json --json`。
6. 将 `MINIMAX_API_KEY` 写入用户级环境变量，便于后续手工联调。

## 结果

- `real-provider-validation-latest.md`：`status=pass`
- `delivery-closeout-latest.md`：`status=pass`
- `delivery-closeout-latest.md`：`milestone=ready_for_business_handoff`
- Mode A smoke：`provider=external_http`
- Mode A smoke：`resolution=minimax_bridge_success`

## 产物

- `docs/dev/real-provider-validation-latest.json`
- `docs/dev/real-provider-validation-latest.md`
- `docs/dev/history/real_provider_validation_20260421_100719.json`
- `docs/dev/history/real_provider_validation_20260421_100719.md`
- `docs/dev/delivery-closeout-latest.json`
- `docs/dev/delivery-closeout-latest.md`
- `docs/dev/history/delivery_closeout_20260421_100816.json`
- `docs/dev/history/delivery_closeout_20260421_100816.md`

## 注意

- 代码仓库内没有写入明文 API Key。
- API Key 已写入用户级环境变量 `MINIMAX_API_KEY`。
- 当前已经打开的旧 PowerShell 会话不会自动刷新这个用户级环境变量。
- 如果要在旧 shell 里立刻使用，先执行：

```powershell
$env:MINIMAX_API_KEY = [Environment]::GetEnvironmentVariable('MINIMAX_API_KEY', 'User')
```

- 新开的 PowerShell 会话应可直接读取该环境变量。
