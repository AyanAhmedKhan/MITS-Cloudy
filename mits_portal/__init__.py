try:
    import pymysql
    pymysql.install_as_MySQLdb()
except Exception:
    # Safe to ignore if driver isn't available during non-DB operations
    pass


