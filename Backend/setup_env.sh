#!/bin/bash
# 这个脚本创建一个Python虚拟环境并安装所有必需的依赖包

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}正在为Azure OpenAI和AI Search项目创建环境...${NC}"

# 检查Python版本
python_version=$(python --version 2>&1)
echo -e "检测到Python版本: ${GREEN}$python_version${NC}"

# 检查virtualenv是否已安装
if ! command -v virtualenv &> /dev/null; then
    echo -e "${YELLOW}virtualenv未安装，正在安装...${NC}"
    pip install virtualenv
fi

# 创建虚拟环境
echo -e "${YELLOW}创建虚拟环境: azure_openai_env${NC}"
virtualenv azure_openai_env

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source azure_openai_env/bin/activate

# 升级pip
echo -e "${YELLOW}升级pip...${NC}"
pip install --upgrade pip

# 安装依赖
echo -e "${YELLOW}安装项目依赖...${NC}"
pip install -r requirements.txt

echo -e "${GREEN}所有依赖已安装完成!${NC}"
echo -e "${YELLOW}你现在可以使用以下命令激活环境:${NC}"
echo -e "${GREEN}source azure_openai_env/bin/activate${NC}"

# 列出已安装的包
echo -e "${YELLOW}已安装的包:${NC}"
pip list

echo -e "${GREEN}环境设置完成!${NC}"