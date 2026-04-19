from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-qiaoya",
    version="1.0.0",
    description="敲鸭社区 CLI — 通过命令行与 https://code.xhyovo.cn/ 交互",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    package_data={
        "cli_anything.qiaoya": ["skills/*.md"],
    },
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "qiaoya=cli_anything.qiaoya.qiaoya_cli:main",
            "cli-anything-qiaoya=cli_anything.qiaoya.qiaoya_cli:main",
        ],
    },
    python_requires=">=3.10",
)
