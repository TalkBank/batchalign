@echo on
echo step 1
pip install .
echo step 2
cd baln\opt\CLANUtils\unix
echo step 3
make
echo step 4
mkdir -p %PREFIX%\bin
mv bin\* %PREFIX%\bin
chmod u+x %PREFIX%\bin\*
