@echo on
dir
pip install .
cd baln\opt\CLANUtils\src
make
cd ..\unix
mkdir -p %PREFIX%\bin
mv bin\* %PREFIX%\bin
chmod u+x %PREFIX%\bin\*
