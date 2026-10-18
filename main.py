import os
from pathlib import Path
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values
import yaml

app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

DEFAULTS={"port":8000,"workers":1,"debug":False,"log_level":"info","api_key":"default-secret-000"}

def coerce(key,value):
    key=key.lower()
    if key in ("port","workers"):
        return int(value)
    if key=="debug":
        if isinstance(value,bool):
            return value
        return str(value).strip().lower() in ("true","1","yes","on")
    return str(value)

def normalize_layer(layer,alias=False):
    result={}
    for key,value in layer.items():
        if value is None:
            continue
        key=str(key).lower()
        if alias and key=="num_workers":
            key="workers"
        elif key.startswith("app_"):
            key=key[4:]
        if key=="env":
            continue
        result[key]=value
    return result

@app.get("/effective-config")
def effective_config(request:Request):
    config=DEFAULTS.copy()
    env_name=os.environ.get("APP_ENV","development")
    yaml_path=Path(f"config.{env_name}.yaml")
    if yaml_path.exists():
        with yaml_path.open() as f:
            yaml_layer=yaml.safe_load(f) or {}
        config.update(normalize_layer(yaml_layer))
    env_file=dotenv_values(".env")
    config.update(normalize_layer(env_file,alias=True))
    os_layer={k:v for k,v in os.environ.items() if k.startswith("APP_") and k!="APP_ENV"}
    config.update(normalize_layer(os_layer))
    for item in request.query_params.getlist("set"):
        if "=" in item:
            key,value=item.split("=",1)
            key=key.strip().lower()
            if key:
                config[key]=value
    result={}
    for key,value in config.items():
        try:
            result[key]=coerce(key,value)
        except (ValueError,TypeError):
            result[key]=value
    result["api_key"]="****"
    return result

@app.get("/")
def root():
    return {"message":"Config Merge API","endpoint":"/effective-config"}
