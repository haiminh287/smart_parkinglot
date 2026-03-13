---
name: database-migration
description: 'Kỹ năng quản lý Database Migration an toàn. Bao gồm tạo migration, rollback strategy, seed data, và best practices.'
---

# 🗄️ Kỹ năng Quản lý Database Migration

## Mục đích
Skill này hướng dẫn quy trình migration database an toàn, đảm bảo không mất dữ liệu và luôn có phương án rollback.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Cần tạo/thay đổi database schema
- Cần migration dữ liệu giữa các schema versions
- Cần seed dữ liệu ban đầu
- Cần rollback migration khi có lỗi

## Quy trình Thực hiện

### 1. Nguyên tắc Migration An toàn
- ✅ Mỗi migration file là **idempotent** (chạy lại không gây lỗi)
- ✅ Mỗi migration file có **up()** và **down()** (rollback)
- ✅ **KHÔNG BAO GIỜ** sửa migration đã chạy trên production
- ✅ Tạo migration MỚI để thay đổi schema
- ✅ Test migration trên staging trước khi chạy production
- ❌ **KHÔNG** dùng `DROP TABLE` trực tiếp – dùng migration framework

### 2. Naming Convention
```
YYYYMMDDHHMMSS-descriptive-name.js
Ví dụ:
20260308120000-create-users-table.js
20260308120100-add-email-index-to-users.js
20260308120200-create-posts-table.js
```

### 3. Migration Template
```javascript
// migrations/20260308120000-create-users-table.js
'use strict';

module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('users', {
      id: {
        type: Sequelize.UUID,
        defaultValue: Sequelize.UUIDV4,
        primaryKey: true,
      },
      email: {
        type: Sequelize.STRING(255),
        allowNull: false,
        unique: true,
      },
      password_hash: {
        type: Sequelize.STRING(255),
        allowNull: false,
      },
      name: {
        type: Sequelize.STRING(100),
        allowNull: false,
      },
      role: {
        type: Sequelize.ENUM('user', 'admin'),
        defaultValue: 'user',
      },
      is_active: {
        type: Sequelize.BOOLEAN,
        defaultValue: true,
      },
      created_at: {
        type: Sequelize.DATE,
        defaultValue: Sequelize.NOW,
      },
      updated_at: {
        type: Sequelize.DATE,
        defaultValue: Sequelize.NOW,
      },
    });

    // Add indexes
    await queryInterface.addIndex('users', ['email'], { unique: true });
    await queryInterface.addIndex('users', ['role']);
  },

  async down(queryInterface) {
    await queryInterface.dropTable('users');
  },
};
```

### 4. Checklist Trước khi Chạy Migration
- [ ] Đã backup database (nếu production)
- [ ] Migration có cả `up()` và `down()`
- [ ] Đã test rollback trên development
- [ ] Không có breaking changes với code hiện tại
- [ ] Index strategy đã được review
- [ ] Performance impact đã được đánh giá (large tables)
- [ ] Downtime estimation (nếu cần)

### 5. Seed Data Template
```javascript
// seeders/20260308120000-demo-users.js
'use strict';
const bcrypt = require('bcrypt');

module.exports = {
  async up(queryInterface) {
    const passwordHash = await bcrypt.hash('P@ssw0rd123', 12);
    await queryInterface.bulkInsert('users', [
      {
        id: '550e8400-e29b-41d4-a716-446655440000',
        email: 'admin@example.com',
        password_hash: passwordHash,
        name: 'System Admin',
        role: 'admin',
        is_active: true,
        created_at: new Date(),
        updated_at: new Date(),
      },
    ]);
  },

  async down(queryInterface) {
    await queryInterface.bulkDelete('users', null, {});
  },
};
```

### 6. Lệnh thường dùng
```bash
# Tạo migration mới
npx sequelize-cli migration:generate --name create-users-table

# Chạy tất cả migration pending
npx sequelize-cli db:migrate

# Rollback migration cuối cùng
npx sequelize-cli db:migrate:undo

# Rollback tất cả
npx sequelize-cli db:migrate:undo:all

# Chạy seed data
npx sequelize-cli db:seed:all

# Kiểm tra status
npx sequelize-cli db:migrate:status
```
