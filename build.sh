pip install .
make -j8 -C ./baln/opt/CLANUtils/src/ -f "makefile.$(UNAME)"
mkdir -p $PREFIX/bin
ls ./baln/opt/CLANUtils/unix/bin/
mv ./baln/opt/CLANUtils/unix/bin/* $PREFIX/bin
chmod u+x $PREFIX/bin/*
