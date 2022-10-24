pip install .
make -C ./baln/opt/CLANUtils/src/ -f Makefile.Windows
mkdir -p %PREFIX%/bin
rem mv ./baln/opt/CLANUtils/unix/bin/* $PREFIX/bin
rem chmod u+x $PREFIX/bin/*

