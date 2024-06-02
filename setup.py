import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ipy_agent",
    version="0.0.4",
    author="Baptiste Ferrand",
    author_email="bferrand.maths@gmail.com",
    description="An AI assistant designed to be integrated in an IPython shell.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/B4PT0R/ipy_agent",
    packages=setuptools.find_packages(),
        package_data={
        'ipy_agent': [
            'default_preprompt.txt',
            'init_shell.py'
        ]
    },
    entry_points={
        'console_scripts': [
            'ipy_agent=ipy_agent.main:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "ipython",
        "PyPDF2",
        "beautifulsoup4",
        "python-docx",
        "get-gecko-driver",
        "google-api-python-client",
        "litellm",
        "numpy",
        "odfpy",
        "openai",
        "pydub",
        "pynput",
        "requests",
        "selenium",
        "sounddevice",
        "tiktoken"
    ],
    python_requires='>=3.9',
)
