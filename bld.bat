@echo on
pip install .
cd baln\opt\CLANUtils\unix
REM make
mkdir -p %PREFIX%\bin
mv bin\* %PREFIX%\bin
chmod u+x %PREFIX%\bin\*
