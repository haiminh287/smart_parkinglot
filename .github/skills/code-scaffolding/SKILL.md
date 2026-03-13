---
name: code-scaffolding
description: 'Kỹ năng khởi tạo dự án nhanh. Tự động tạo cấu trúc thư mục, boilerplate code, config files, và setup development environment.'
---

# 🏗️ Kỹ năng Khởi tạo Dự án (Project Scaffolding Skill)

## Mục đích
Skill này giúp Architect và Implementer nhanh chóng tạo skeleton project với đầy đủ boilerplate, config, và structure chuẩn.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Khởi tạo dự án mới từ đầu
- Cần setup project structure chuẩn
- Cần tạo boilerplate cho một stack cụ thể

## Supported Stacks

### Stack 1: Node.js + Express + TypeScript + PostgreSQL
```
project/
├── src/
│   ├── config/
│   │   ├── database.ts         # Database connection config
│   │   ├── server.ts           # Server configuration
│   │   ├── logger.ts           # Winston/Pino logger setup
│   │   └── index.ts            # Config barrel export
│   ├── models/                 # Sequelize/TypeORM models
│   ├── repositories/           # Data Access Layer
│   ├── services/               # Business Logic Layer
│   ├── controllers/            # Request Handlers
│   ├── routes/                 # Express route definitions
│   │   ├── v1/                 # API version 1
│   │   │   ├── user.routes.ts
│   │   │   └── index.ts
│   │   └── index.ts
│   ├── middlewares/
│   │   ├── auth.middleware.ts
│   │   ├── error-handler.middleware.ts
│   │   ├── validator.middleware.ts
│   │   ├── rate-limiter.middleware.ts
│   │   └── request-logger.middleware.ts
│   ├── errors/
│   │   ├── app-error.ts
│   │   ├── validation-error.ts
│   │   ├── not-found-error.ts
│   │   ├── auth-error.ts
│   │   └── database-error.ts
│   ├── utils/
│   │   ├── constants.ts
│   │   ├── helpers.ts
│   │   └── response-formatter.ts  
│   ├── types/                   # TypeScript type definitions
│   │   └── index.d.ts
│   └── app.ts                   # Application entry
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── docs/
│   ├── status.yaml
│   ├── prd/
│   ├── architecture/
│   ├── api/
│   └── testing/
├── infra/
│   └── docker/
│       └── Dockerfile
├── .env.example
├── .gitignore
├── .eslintrc.json
├── .prettierrc
├── tsconfig.json
├── package.json
├── docker-compose.yml
└── README.md
```

### Stack 2: Next.js + TypeScript + Prisma
```
project/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   └── api/                # API routes
│   │       └── v1/
│   ├── components/             # React components
│   │   ├── ui/                 # Base UI components
│   │   ├── features/           # Feature-specific components
│   │   └── layouts/            # Layout components
│   ├── lib/                    # Utility libraries
│   │   ├── prisma.ts           # Prisma client instance
│   │   ├── auth.ts             # Authentication helpers
│   │   └── utils.ts
│   ├── hooks/                  # Custom React hooks
│   ├── types/                  # TypeScript types
│   └── styles/                 # Additional styles
├── prisma/
│   ├── schema.prisma           # Database schema
│   ├── migrations/
│   └── seed.ts
├── public/                     # Static assets
├── tests/
└── ...
```

### Stack 3: Python + FastAPI + SQLAlchemy
```
project/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic
│   ├── api/                    # API endpoints
│   │   └── v1/
│   ├── core/
│   │   ├── security.py         # Auth utilities
│   │   ├── database.py         # Database connection
│   │   └── exceptions.py       # Custom exceptions
│   └── utils/
├── tests/
├── alembic/                    # Database migrations
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Boilerplate Files

### .gitignore (Universal)
```
# Dependencies
node_modules/
__pycache__/
venv/
.venv/

# Environment
.env
.env.local
.env.*.local

# Build
dist/
build/
*.pyc

# IDE
.vscode/settings.json
.idea/

# Testing
coverage/
.nyc_output/
test-results/
htmlcov/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
```

### .eslintrc.json (TypeScript)
```json
{
  "root": true,
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint"],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "prettier"
  ],
  "rules": {
    "no-console": "warn",
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/explicit-function-return-type": "warn",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}
```

### .prettierrc
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100,
  "endOfLine": "lf"
}
```
