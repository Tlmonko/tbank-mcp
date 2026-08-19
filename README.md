# tbank-cli-mcp

Локальный read-only CLI и stdio MCP для чтения данных личного кабинета
физического лица в Т‑Банке. Постоянный HTTP-сервер, облачный сервис, Docker и
background daemon не используются.

## Проверенные read-only контракты

Контракты ниже сверены 19 августа 2026 года по текущему web-клиенту в
авторизованном кабинете: read-only навигации и загруженным public JavaScript
bundles. Не сохранялись HAR, cookies, токены, ID или реальные ответы.

| Ресурс | Method и путь | Жёстко заданные параметры |
|---|---|---|
| Продукты / счета | `GET /api/common/v1/accounts_light_ib` | `appName`, `appVersion`, `platform`, `origin`, `sessionid` |
| Операции / деталь | `GET /mybank/api/operations/timeline/public/legacy/v1/operations` | `appName`, `appVersion`, `origin`, `sessionid`; список добавляет `account`, `start`, `end`, деталь — `operationId` |
| Чек | `GET /api/common/v1/shopping_receipt` | `operationId`, `sessionid` |
| Выписки | `GET /api/common/v1/statements` | `account`, `itemsOrder=desc`, `sessionid` |

Даты списка операций переводятся из `YYYY-MM-DD` в Unix milliseconds, границы
периода включаются. Чек доступен только для части операций; web-клиент запрашивает
его по authorization ID операции. Выписки возвращаются как массив в `payload`, а
чеки — как `payload.receipt` с суммой и позициями.

Reference — MIT-проект
[`jfk9w-go/tinkoff-api`](https://github.com/jfk9w-go/tinkoff-api); его старый
SMS-flow не копируется.

## Статус и риски

Это неофициальный клиент внутреннего web API. Контракт может измениться после
обновления сайта, а использование может противоречить условиям Т‑Банка. Проект
не имеет отношения к Т‑Банку. Платежи, переводы, пополнения, управление картами,
лимитами, заявки, настройки и сообщения в банк намеренно не реализованы.

## Требования и установка

Нужны Python 3.11+ и локальный доступ к своей уже авторизованной браузерной
сессии. Установка в виртуальное окружение:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install ".[dev]"
```

## Локальная сессия

Пароль и SMS/OTP через CLI не вводятся. В браузере вручную подготовьте локальный
JSON со secret fields `cookies` и `session_id`; опциональны `origin` (только
`web,ib5,platform` или вариант для junior) и `expires_at`. Значения не печатаются
ни CLI, ни MCP.

Не вставляйте этот файл в git и не присылайте его агенту. Импорт:

```bash
tbank auth import /secure/path/session.json
tbank auth status --json
```

По умолчанию сессия хранится в `~/.config/tbank-cli/session.json` с правами
`0600`. Путь меняется через `TBANK_SESSION_FILE`. Существующая сессия не
перезаписывается без `--replace`. `auth status` возвращает только
`authenticated`, `expired` или `missing`.

## CLI

Успешный результат — JSON в stdout, диагностика — редактируемый JSON в stderr:

```bash
tbank products list --json
tbank accounts list --json
tbank operations list --account <account-id> --from 2026-08-01 --to 2026-08-02 --json
tbank operation get --id <operation-id> --json
tbank receipt get --operation <authorization-id> --json
tbank statements list --account <account-id> --json
```

Произвольных `request`, URL, HTTP method, заголовков и тела нет.

## MCP stdio

Инструмент запускается только как дочерний stdio-процесс. Порт и HTTP server не
поднимаются; протокол остаётся в stdout, логи — в stderr. Сервер публикует только
read-only tools: `list_products`,
`list_accounts`, `list_operations`, `get_operation`, `get_receipt`,
`list_statements`.

Пример для Hermes:

```yaml
mcp_servers:
  tbank:
    command: "tbank-mcp"
    args: []
    env:
      TBANK_SESSION_FILE: "/home/user/.config/tbank-cli/session.json"
```

Пример для Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.tbank]
command = "tbank-mcp"
args = []

[mcp_servers.tbank.env]
TBANK_SESSION_FILE = "/home/user/.config/tbank-cli/session.json"
```

## Тесты и линтер

```bash
python -m pytest
ruff check src tests
```

Тесты используют только синтетические fixtures и fake transport; живые запросы
в банк не выполняются.

## Security notes

- Никогда не коммитьте `.env`, `*.har`, `*.pem`, `*.key`, `*session*.json`,
  cookies, session/access/refresh/bearer tokens, session/device IDs, телефон,
  номера карт/счетов, паспортные и платёжные данные или реальные JSON-ответы.
- Ошибки CLI и MCP не содержат request headers, cookies, query с session ID или
  полный банковский response body.
- Любые POST/PUT/PATCH/DELETE заблокированы архитектурой клиента.

## Troubleshooting

`auth status` показывает `missing`, если файл не импортирован, и `expired`, если
истёк `expires_at` или JSON повреждён. Повторите ручной вход в браузере и
импортируйте новый export с `--replace`.

Если после обновления сайта запрос вернул ошибку, повторите проверку контракта в
Network: внутренний API нестабилен и может потребовать изменения адаптера.
