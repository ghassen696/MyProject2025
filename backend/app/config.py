ELASTICSEARCH_URL = "http://193.95.30.190:9200"
SECRET_KEY = "rveriveivjevsupersecretkey12ded"  # use env variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
SMTP_USERNAME = "huaweitesttest1@gmail.com"
SMTP_PASSWORD = "ordf ylso cjkm koiq"  # generate from Google account
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_FROM = "Huawei Test <huaweitesttest1@gmail.com>"
FRONTEND_URL = "http://193.95.30.190:5173"
INDEX_KPI = "employee_kpi_daily_v3"
INDEX_KPIBATCH = "employee_kpi_summary4"
SKILL_PATTERNS = {
    # Programming Languages
    r'\.py\b|python': ['Python'],
    r'\.js\b|javascript|node': ['JavaScript', 'Node.js'],
    r'\.ts\b|typescript': ['TypeScript'],
    r'\.java\b': ['Java'],
    r'\.cpp\b|\.c\b': ['C/C++'],
    r'\.go\b': ['Go'],
    r'\.rs\b|rust': ['Rust'],
    
    # Frameworks & Libraries
    r'fastapi|router\.py': ['FastAPI', 'Backend Development'],
    r'django': ['Django', 'Backend Development'],
    r'flask': ['Flask', 'Backend Development'],
    r'react|\.tsx\b|\.jsx\b': ['React', 'Frontend Development'],
    r'vue': ['Vue.js', 'Frontend Development'],
    r'angular': ['Angular', 'Frontend Development'],
    
    # Data & AI/ML
    r'pandas|numpy|jupyter': ['Data Analysis', 'Python'],
    r'tensorflow|keras|pytorch': ['Machine Learning', 'Deep Learning'],
    r'sklearn|scikit': ['Machine Learning'],
    r'pipeline': ['Data Pipelines', 'ETL'],
    
    # Databases & Search
    r'elasticsearch|elastic': ['Elasticsearch', 'Search Engineering'],
    r'postgres|postgresql': ['PostgreSQL', 'Database'],
    r'mysql': ['MySQL', 'Database'],
    r'mongodb': ['MongoDB', 'NoSQL'],
    r'redis': ['Redis', 'Caching'],
    
    # DevOps & Tools
    r'docker|dockerfile': ['Docker', 'Containerization'],
    r'kubernetes|k8s': ['Kubernetes', 'Orchestration'],
    r'terraform': ['Terraform', 'IaC'],
    r'jenkins|github actions': ['CI/CD'],
    
    # Development Tools
    r'visual studio code|vscode|code\.exe': ['VS Code', 'Development'],
    r'cursor': ['AI-Assisted Development', 'Development'],
    r'git': ['Git', 'Version Control'],
    
    # Design & Documentation
    r'lucidchart': ['Diagramming', 'System Design'],
    r'figma': ['UI/UX Design'],
    r'\.md\b|markdown': ['Documentation'],
    r'\.tex\b|latex': ['LaTeX', 'Technical Writing'],
    
    # Web & APIs
    r'chrome|edge|browser': ['Web Research'],
    r'api|rest|graphql': ['API Development'],
    r'localhost:\d+': ['Local Development', 'Testing'],
    
    # Business Tools
    r'google (docs|sheets|slides)': ['Google Workspace'],
    r'excel|spreadsheet': ['Data Analysis', 'Excel'],
    r'powerpoint|presentation': ['Presentations'],
    
    # AI Tools
    r'claude|chatgpt|gemini': ['AI Tools', 'Prompt Engineering'],
    r'copilot': ['AI-Assisted Development'],
    
    # Specific Tasks
    r'classification|prediction': ['Machine Learning', 'Classification'],
    r'embedding|vector': ['Vector Search', 'Embeddings'],
    r'kpi|analytics|dashboard': ['Analytics', 'Data Visualization'],
    r'report|summary': ['Reporting', 'Analysis'],
    r'router|endpoint': ['Backend Development', 'API Development'],
}
