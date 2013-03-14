AC_INIT([extremon], [0.3], [frank@apsu.be])
AM_INIT_AUTOMAKE([foreign -Wall -Werror])
AC_PROG_CC
AM_PROG_CC_C_O
AC_CHECK_LIB([pthread], [pthread_create], [PTHREAD=-lpthread])
AC_SUBST([PTHREAD])
AC_CONFIG_HEADERS([config.h])
AC_CHECK_HEADERS([arpa/inet.h])
AC_CHECK_HEADERS([fcntl.h])
AC_CHECK_HEADERS([netdb.h])
AC_CHECK_HEADERS([netinet/in.h])
AC_CHECK_HEADERS([stdlib.h])
AC_CHECK_HEADERS([string.h])
AC_CHECK_HEADERS([sys/socket.h])
AC_CHECK_HEADERS([unistd.h])
AC_CONFIG_FILES([Makefile src/Makefile])
AC_OUTPUT
