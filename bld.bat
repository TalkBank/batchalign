pip install .
cd ./baln/opt/CLANUtils/unix
make -f Makefile.win
mkdir -p %PREFIX%/bin
mv ./bin/* %PREFIX%/bin
chmod u+x %PREFIX%/bin/*
