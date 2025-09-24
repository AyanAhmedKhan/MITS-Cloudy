# 🎓 MITS Cloud - Complete File Management System

A comprehensive, production-ready file management portal for MITS College with advanced features including search, categorization, audit logging, and enhanced sharing capabilities.

## ✨ Features

### 🔐 **Authentication & User Management**
- Domain-restricted signup/login (only @mitsgwalior.in emails)
- User profiles with department assignments
- Faculty status designation
- Role-based access control

### 📚 **Academic Session Management**
- Create and manage academic sessions (2024-25, 2023-24, etc.)
- Activate/deactivate sessions
- Session duplication for easy setup
- Date-based session tracking

### 🏢 **Department Organization**
- Multiple engineering departments (CSE, ECE, ME, CE, IT)
- Department heads assignment
- Active/inactive department status

### 📁 **Advanced File Management**
- **Recursive folder structure** with unlimited nesting
- **File categorization** (Syllabus, Notes, Assignments, etc.)
- **File validation** with supported format restrictions
- **Metadata tracking** (file size, download count, timestamps)
- **Public/Private visibility** controls

### 🔍 **Search & Discovery**
- **Full-text search** across file names, descriptions, and content
- **Filter by department, session, category**
- **Advanced search results** with file previews
- **Search history** and suggestions

### 🔗 **Enhanced Sharing System**
- **Public links** - accessible to anyone
- **Email-restricted** - only specific email addresses
- **Password-protected** - secure access with passwords
- **Download limits** - control usage with max downloads
- **Expiry dates** - time-limited access
- **Share analytics** - track usage and downloads

### 📊 **Audit & Analytics**
- **Complete audit trail** for all file operations
- **Download tracking** with IP addresses and user agents
- **User activity monitoring** for compliance
- **File access logs** for security

### 🔔 **Notification System**
- **File sharing notifications**
- **Session activation alerts**
- **System announcements**
- **Read/unread status tracking**

### 🎨 **Modern UI/UX**
- **Tailwind CSS** with blue/white theme
- **Responsive design** for all devices
- **Interactive folder trees** with expand/collapse
- **Drag & drop** file uploads (planned)
- **Real-time updates** and notifications

## 🚀 **Quick Start**

### 1. **Environment Setup**
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **Database Setup**
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Setup initial data
python manage.py setup_data
```

### 3. **Run the Server**
```bash
python manage.py runserver
```

### 4. **Access the System**
- **Main Portal**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **Dashboard**: http://127.0.0.1:8000/dashboard/
- **Faculty Page**: http://127.0.0.1:8000/faculty/

## 🏗️ **System Architecture**

### **Backend Stack**
- **Django 4.2** - Core web framework
- **Django REST Framework** - API endpoints
- **SQLite** - Development database (PostgreSQL ready)
- **WhiteNoise** - Static file serving
- **CORS Headers** - Cross-origin support

### **Data Models**
```
UserProfile ← User (Django Auth)
    ↓
Department ← AcademicSession
    ↓
Folder (self-referential)
    ↓
FileItem ← FileCategory
    ↓
ShareLink
    ↓
FileAuditLog
```

### **API Endpoints**
- `GET/POST /api/sessions/` - Academic sessions
- `GET/POST /api/departments/` - Departments
- `GET/POST /api/categories/` - File categories
- `GET/POST /api/folders/` - Folder management
- `GET/POST /api/files/` - File uploads
- `GET/POST /api/share/` - Share link creation
- `GET /api/search/` - File search
- `GET /api/public-tree/` - Public file tree

## 📱 **User Interfaces**

### **Landing Page** (`/`)
- Browse public files by session/department
- No authentication required
- Responsive grid layout
- File previews and metadata

### **Dashboard** (`/dashboard/`)
- **Upload Interface**: Multi-step file/folder creation
- **File Management**: View, delete, share your files
- **Folder Tree**: Interactive folder navigation
- **Search**: Find files across the system
- **Old Sessions**: Browse previous academic years

### **Faculty Page** (`/faculty/`)
- **Active Session Only**: Upload to current sessions
- **Department Selection**: Choose target department
- **Folder Integration**: Upload to existing folders
- **Public/Private Control**: Set file visibility

### **Admin Panel** (`/admin/`)
- **User Management**: Control access and permissions
- **Session Control**: Activate/deactivate sessions
- **Department Management**: Add/edit departments
- **File Categories**: Organize content types
- **Audit Logs**: Monitor system activity

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost/mits_portal

# Email settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### **File Upload Settings**
```python
# Supported file types
ALLOWED_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'ppt', 'pptx',
    'xls', 'xlsx', 'txt', 'zip', 'rar',
    'jpg', 'jpeg', 'png', 'gif'
]

# Maximum file size (default: 50MB)
MAX_UPLOAD_SIZE = 52428800
```

## 📊 **Usage Examples**

### **Creating a Share Link**
1. Navigate to Dashboard → Your Files
2. Click "Share" on any file
3. Choose share type:
   - **Public**: Anyone can access
   - **Email**: Restricted to specific email
   - **Password**: Protected with password
4. Set optional limits (downloads, expiry)
5. Generate and copy the share link

### **Organizing Files**
1. **Create Folders**: Use the upload form with folder name
2. **Categorize**: Assign files to categories (Syllabus, Notes, etc.)
3. **Structure**: Organize by session → department → folder → files
4. **Visibility**: Set public/private for each item

### **Searching Content**
1. Use the search bar on dashboard
2. Search by filename, description, or content
3. Filter results by department, session, or category
4. View file metadata and download directly

## 🛡️ **Security Features**

- **CSRF Protection** on all forms
- **File Type Validation** to prevent malicious uploads
- **Access Control** based on user roles and ownership
- **Audit Logging** for compliance and security
- **Session Management** with proper authentication
- **Input Sanitization** to prevent XSS attacks

## 📈 **Performance & Scalability**

- **Database Indexing** on frequently queried fields
- **File Storage Optimization** with organized directory structure
- **Caching Ready** for production deployment
- **API Pagination** for large datasets
- **Background Tasks** support for file processing

## 🚀 **Deployment**

### **Production Checklist**
- [ ] Set `DEBUG=False`
- [ ] Configure production database (PostgreSQL)
- [ ] Set up static file serving (CDN/WhiteNoise)
- [ ] Configure email backend
- [ ] Set up SSL/TLS certificates
- [ ] Configure backup strategies
- [ ] Set up monitoring and logging

### **Docker Support** (Optional)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 **Support**

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

---

**MITS Cloud** - Empowering education through organized file management and collaboration. 🎓✨
