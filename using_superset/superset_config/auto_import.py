import time, os, subprocess

EXPORT_FILE = "/app/superset_home/dashboard_export_20260514T151310.zip"
FLAG_FILE = "/app/superset_home/imported.flag"

def init_superset():
    print(">>> Đang khởi tạo database...")
    subprocess.run(["superset", "db", "upgrade"], check=True)
    
    print(">>> Đang tạo tài khoản admin...")
    subprocess.run([
        "superset", "fab", "create-admin",
        "--username", "admin",
        "--firstname", "Superset",
        "--lastname", "Admin",
        "--email", "admin@superset.com",
        "--password", "admin"
    ], check=False)
    
    print(">>> Đang thiết lập các role mặc định...")
    subprocess.run(["superset", "init"], check=True)

def main():
    time.sleep(15)
    
    # Nếu file DB chưa được tạo hoặc rất nhỏ, chúng ta sẽ init
    db_path = "/app/superset_home/superset.db"
    if not os.path.exists(db_path) or os.path.getsize(db_path) < 100000:
        init_superset()

    if os.path.exists(FLAG_FILE):
        print(">>> Đã import trước đó, bỏ qua.")
        return
    if not os.path.exists(EXPORT_FILE):
        print(">>> Không tìm thấy file export dashboard.")
        return

    print(">>> Đang import dashboard...")
    result = subprocess.run(
        ["superset", "import-dashboards", "--path", EXPORT_FILE, "--username", "admin"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(">>> Lỗi import:", result.stderr)
        return
    print(result.stdout)
    
    # Tạo cờ đã import
    with open(FLAG_FILE, 'w') as f:
        f.write('done')

if __name__ == "__main__":
    main()