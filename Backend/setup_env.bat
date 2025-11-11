@echo off
echo 正在为Azure OpenAI和AI Search项目创建环境...

REM 检查Python版本
python --version
if %ERRORLEVEL% NEQ 0 (
    echo Python未安装或不在PATH中！
    echo 请安装Python并确保它在PATH中。
    exit /b
)

REM 检查virtualenv
pip show virtualenv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo virtualenv未安装，正在安装...
    pip install virtualenv
)

REM 创建虚拟环境
echo 创建虚拟环境: azure_openai_env
virtualenv azure_openai_env

REM 激活虚拟环境
echo 激活虚拟环境...
call azure_openai_env\Scripts\activate.bat

REM 升级pip
echo 升级pip...
pip install --upgrade pip

REM 安装依赖
echo 安装项目依赖...
pip install -r requirements.txt

echo 所有依赖已安装完成!
echo 你现在可以使用以下命令激活环境:
echo call azure_openai_env\Scripts\activate.bat

REM 列出已安装的包
echo 已安装的包:
pip list

echo 环境设置完成!