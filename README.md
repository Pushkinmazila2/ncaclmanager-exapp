# ncaclmanager-exapp
ncaclmanager-exapp


```
ncaclmanager-exapp/
├── src/
│   ├── main.py              ✅ FastAPI приложение + регистрация в NC
│   ├── models/settings.py   ✅ Pydantic модели
│   ├── services/
│   │   ├── db.py            ✅ SQLite настройки
│   │   ├── agent.py         ✅ HTTP клиент к NcAclAgent (PFX→PEM конвертация)
│   │   └── auth.py          ✅ Проверка прав через заголовки AppAPI
│   └── routers/
│       ├── lifecycle.py     ✅ /heartbeat /init /enabled
│       ├── acl.py           ✅ /api/acl
│       ├── groups.py        ✅ /api/groups
│       ├── users.py         ✅ /api/users
│       ├── settings.py      ✅ /api/settings + маппинги + upload
│       └── ui_actions.py    ✅ /ui/file-action-acl
├── Dockerfile                ✅
├── docker-compose.yml         ✅
├── deploy.json                ✅ манифест AppAPI
└── appinfo/info.xml            ✅
```
