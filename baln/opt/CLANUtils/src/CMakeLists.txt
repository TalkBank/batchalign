# Copyright 2022 Brian MacWhinney
# The use of this program is subject to the GNU Public License
# as stated in the attached "gpl.txt" file.

# This is a fork of UnixCLAN, built for TalkBank's Batchalign
# pipeline.
#
# Sources for the program are available at github.com/TalkBank/batchalign

cmake_minimum_required(VERSION 3.20)
project(CLANUtils)
set(CMAKE_CXX_STANDARD 14)

# put outputs to bin
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "./bin")

# define to copmile unix
add_compile_definitions(UNX)

#### shared libraries ####
# create libaries to link against
add_library(c_ver OBJECT c_ver.cpp)
add_library(cut OBJECT cutt.cpp)
add_library(cxml OBJECT cutt-xml.cpp)
add_library(stp OBJECT stringparser.cpp)
add_library(fntc OBJECT fontconvert.cpp)

# link all targets to the above libraries
link_libraries(c_ver cut cxml stp fntc)

#### targets ####
# these targets are added here on an as-needed
# basis for batchalign

# utilities
add_executable(flo flo.cpp)
add_executable(lowcase lowcase.cpp)
add_executable(fixbullets FixBullets.cpp)
add_executable(chstring chstring.cpp)
add_executable(retrace retrace.cpp)
add_executable(kwal kwal.cpp)

# conversion commands
add_executable(elan2chat Elan2Chat.cpp)
add_executable(chat2elan Chat2Elan.cpp)
add_executable(praat2chat Praat2Chat.cpp)
add_executable(chat2praat Chat2Praat.cpp)

