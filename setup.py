import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="andperf",
    version="0.0.2-beta1",
    author="WangWei",
    author_email="2317073226@qq.com",
    description="Android 性能调优工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/weixinfree/AndPerf",
    packages=setuptools.find_packages(),
    install_requires=[
        'matplotlib==3.0.0',
        'numpy==1.15.1',
        'pandas==0.23.4'],
    entry_points={
        'console_scripts': [
            'andperf=andperf.andperf:main'
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
