import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, redirect, url_for
from config import Config
from extensions import db, jwt

load_dotenv()
def create_app(config_class=Config):
    app=Flask(__name__); app.config.from_object(config_class); Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True,exist_ok=True); Path(app.instance_path).mkdir(parents=True,exist_ok=True); db.init_app(app); jwt.init_app(app)
    from services.security import configure_security
    configure_security(app)
    from routes import BLUEPRINTS
    for blueprint in BLUEPRINTS:app.register_blueprint(blueprint)
    @app.get("/")
    def home():
        return redirect(url_for("admin.web_login"))
    @app.get("/health")
    def health():return {"success":True,"message":"Field Task Manager API is healthy","data":{}}
    @app.errorhandler(404)
    def not_found(_):return {"success":False,"message":"Resource not found","data":{}},404
    @app.errorhandler(413)
    def too_large(_):return {"success":False,"message":"File exceeds upload limit","data":{}},413
    return app

app=create_app()
if __name__=="__main__":
    with app.app_context():db.create_all()
    app.run(host=os.getenv("HOST","0.0.0.0"),port=int(os.getenv("PORT","5000")),debug=os.getenv("FLASK_ENV")=="development")
