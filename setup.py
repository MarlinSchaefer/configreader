from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(name="configreader",
          version="1.0.0",
          description="Configuration file reader with sub-sections and interprable values.",
          license="MIT",
          author="Marlin Benedikt Schäfer",
          package_dir={"": "src"},
          packages=find_packages(where="src"),
          )
