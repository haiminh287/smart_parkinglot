---
name: api-development
description: 'Bộ kỹ năng phát triển RESTful API chuẩn doanh nghiệp. Bao gồm thiết kế endpoint, validation, middleware, error handling, và OpenAPI documentation.'
---

# 🌐 Kỹ năng Phát triển API (RESTful API Development Skill)

## Mục đích
Skill này cung cấp quy trình và template chuẩn để phát triển RESTful API chất lượng production-grade.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Cần thiết kế và triển khai API endpoints mới
- Cần implement CRUD operations
- Cần thiết lập authentication/authorization
- Cần tạo OpenAPI documentation

## Quy trình Thực hiện

### 1. Thiết kế API Endpoint
```yaml
# Quy ước URL format
GET     /api/v1/resources          # Lấy danh sách
GET     /api/v1/resources/:id      # Lấy chi tiết
POST    /api/v1/resources          # Tạo mới
PUT     /api/v1/resources/:id      # Cập nhật toàn bộ
PATCH   /api/v1/resources/:id      # Cập nhật một phần
DELETE  /api/v1/resources/:id      # Xóa

# Relationships
GET     /api/v1/users/:userId/posts        # Posts của user
POST    /api/v1/users/:userId/posts        # Tạo post cho user

# Filtering & Pagination
GET     /api/v1/resources?page=1&limit=20&sort=-createdAt&filter[status]=active
```

### 2. Response Format Chuẩn

#### Thành công (Success)
```json
{
  "success": true,
  "data": { /* payload */ },
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5
  }
}
```

#### Lỗi (Error)
```json
{
  "success": false,
  "error": {
    "code": "ERR_VALIDATION",
    "message": "Dữ liệu không hợp lệ",
    "details": [
      {
        "field": "email",
        "message": "Email không đúng định dạng"
      }
    ]
  }
}
```

### 3. Middleware Stack
```javascript
// Thứ tự middleware cần áp dụng
app.use(helmet());               // Security headers
app.use(cors(corsOptions));      // CORS
app.use(rateLimit(limiter));     // Rate limiting
app.use(express.json());         // Body parser
app.use(requestLogger);          // Request logging
app.use(authenticate);           // Authentication
app.use('/api/v1', apiRoutes);   // Routes
app.use(errorHandler);           // Global error handler
```

### 4. Validation Layer
```javascript
// Sử dụng Joi hoặc Zod cho input validation
const createUserSchema = z.object({
  name: z.string().min(2).max(100),
  email: z.string().email(),
  password: z.string().min(8).regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/),
  role: z.enum(['user', 'admin']).default('user'),
});

// Middleware validation
const validate = (schema) => (req, res, next) => {
  const result = schema.safeParse(req.body);
  if (!result.success) {
    throw new ValidationError(result.error.flatten());
  }
  req.validatedData = result.data;
  next();
};
```

### 5. Controller Template
```javascript
class UserController {
  constructor(userService) {
    this.userService = userService;
  }

  async getAll(req, res, next) {
    try {
      const { page, limit, sort, filter } = req.query;
      const result = await this.userService.findAll({ page, limit, sort, filter });
      res.status(200).json({
        success: true,
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      next(error);
    }
  }

  async getById(req, res, next) {
    try {
      const user = await this.userService.findById(req.params.id);
      if (!user) throw new NotFoundError('User not found');
      res.status(200).json({ success: true, data: user });
    } catch (error) {
      next(error);
    }
  }

  async create(req, res, next) {
    try {
      const user = await this.userService.create(req.validatedData);
      res.status(201).json({ success: true, data: user });
    } catch (error) {
      next(error);
    }
  }
}
```

### 6. HTTP Status Codes
| Code | Ý nghĩa | Khi nào dùng |
|------|---------|-------------|
| 200 | OK | GET thành công, PUT/PATCH thành công |
| 201 | Created | POST tạo resource mới thành công |
| 204 | No Content | DELETE thành công |
| 400 | Bad Request | Input validation failed |
| 401 | Unauthorized | Chưa xác thực |
| 403 | Forbidden | Không có quyền truy cập |
| 404 | Not Found | Resource không tồn tại |
| 409 | Conflict | Duplicate resource (email đã tồn tại) |
| 422 | Unprocessable | Business logic validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Lỗi server không dự đoán được |
