pip install .
make -d -C ./baln/opt/CLANUtils/src/ -f Makefile.Windows
dir $PREFIX/bin
rem mkdir -p $PREFIX/bin
rem mv ./baln/opt/CLANUtils/unix/bin/* $PREFIX/bin
rem chmod u+x $PREFIX/bin/*

