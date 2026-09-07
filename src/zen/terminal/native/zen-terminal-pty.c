/* Minimal framed-stdin / raw-stdout PTY bridge. No shell parsing. */
#define _DARWIN_C_SOURCE
#define _DEFAULT_SOURCE
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#ifdef __APPLE__
#include <util.h>
#else
#include <pty.h>
#endif
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CAP (256U * 1024U)
#define MAX_DIM 1000U
static volatile sig_atomic_t stopping;
static void stop(int sig) { stopping = sig; }
static int nonblock(int fd) {
  int flags = fcntl(fd, F_GETFL);
  return flags < 0 ? -1 : fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}
static int number(const char **p, unsigned limit, unsigned *value) {
  unsigned n = 0;
  const char *s = *p;
  if (*s < '0' || *s > '9') return -1;
  while (*s >= '0' && *s <= '9') {
    unsigned digit = (unsigned)(*s++ - '0');
    if (n > limit / 10 || (n == limit / 10 && digit > limit % 10)) return -1;
    n = n * 10 + digit;
  }
  *p = s; *value = n; return 0;
}
static int dimension(const char *s, unsigned *n) {
  return number(&s, MAX_DIM, n) || *s || !*n ? -1 : 0;
}
static int retryable(void) { return errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK; }
static void consume(unsigned char *buf, size_t *len, size_t n) {
  *len -= n; memmove(buf, buf + n, *len);
}
static void reap(pid_t child, int *status, int *reaped) {
  if (*reaped) return;
  for (int i = 0; i < 100; ++i) {
    pid_t r = waitpid(child, status, WNOHANG);
    if (r == child || (r < 0 && errno == ECHILD)) { *reaped = 1; return; }
    usleep(10000);
  }
  /* Only signal our direct child, never a tmux server or arbitrary process group. */
  kill(child, SIGTERM);
  for (int i = 0; i < 100; ++i) {
    pid_t r = waitpid(child, status, WNOHANG);
    if (r == child || (r < 0 && errno == ECHILD)) { *reaped = 1; return; }
    usleep(10000);
  }
  kill(child, SIGKILL);
  while (waitpid(child, status, 0) < 0 && errno == EINTR) {}
  *reaped = 1;
}
int main(int argc, char **argv) {
  unsigned rows, cols;
  if (argc < 7 || strcmp(argv[1], "--rows") || dimension(argv[2], &rows) ||
      strcmp(argv[3], "--cols") || dimension(argv[4], &cols) ||
      strcmp(argv[5], "--") || argv[6][0] != '/') {
    fprintf(stderr, "zen-terminal-pty: usage: --rows 1..1000 --cols 1..1000 -- /absolute/program [args...]\n");
    return 64;
  }
  struct sigaction sa;
  memset(&sa, 0, sizeof(sa)); sigemptyset(&sa.sa_mask); sa.sa_handler = stop;
  sigaction(SIGHUP, &sa, NULL); sigaction(SIGTERM, &sa, NULL); sigaction(SIGINT, &sa, NULL);
  signal(SIGPIPE, SIG_IGN);
  int errors[2];
  if (pipe(errors) || fcntl(errors[1], F_SETFD, FD_CLOEXEC) < 0) { perror("zen-terminal-pty: pipe"); return 1; }
  struct winsize size = {.ws_row = (unsigned short)rows, .ws_col = (unsigned short)cols};
  int master;
  pid_t child = forkpty(&master, NULL, NULL, &size);
  if (child < 0) { perror("zen-terminal-pty: forkpty"); close(errors[0]); close(errors[1]); return 1; }
  if (!child) {
    close(errors[0]);
    signal(SIGHUP, SIG_DFL); signal(SIGTERM, SIG_DFL); signal(SIGINT, SIG_DFL); signal(SIGPIPE, SIG_DFL);
    execv(argv[6], &argv[6]);
    int failure = errno;
    (void)!write(errors[1], &failure, sizeof(failure));
    _exit(127);
  }
  close(errors[1]);
  int failure = 0;
  ssize_t error_read;
  do { error_read = read(errors[0], &failure, sizeof(failure)); } while (error_read < 0 && errno == EINTR && !stopping);
  close(errors[0]);
  int status = 0, reaped = 0, result = 0;
  if (error_read > 0) {
    fprintf(stderr, "zen-terminal-pty: exec %s: %s\n", argv[6], strerror(failure));
    result = 127; goto cleanup;
  }
  if (nonblock(master) || nonblock(STDIN_FILENO) || nonblock(STDOUT_FILENO)) {
    perror("zen-terminal-pty: nonblocking setup"); result = 1; goto cleanup;
  }
  unsigned char input[CAP], output[CAP];
  size_t in_len = 0, out_len = 0, remaining = 0, header_len = 0;
  char header[64];
  int master_done = 0;
  while (!stopping) {
    if (!reaped && waitpid(child, &status, WNOHANG) == child) reaped = 1;
    if (master_done && !out_len) break;
    struct pollfd fds[3] = {
      {(!master_done && in_len < CAP) ? STDIN_FILENO : -1, POLLIN, 0},
      {(master_done || out_len == CAP) ? -1 : master, (short)(POLLIN | (in_len ? POLLOUT : 0)), 0},
      {STDOUT_FILENO, out_len ? POLLOUT : 0, 0}
    };
    int ready = poll(fds, 3, 100);
    if (ready < 0) { if (errno == EINTR) continue; perror("zen-terminal-pty: poll"); result = 1; break; }
    if (fds[2].revents & (POLLERR | POLLHUP | POLLNVAL)) { result = 1; break; }
    if ((fds[2].revents & POLLOUT) && out_len) {
      ssize_t n = write(STDOUT_FILENO, output, out_len);
      if (n > 0) consume(output, &out_len, (size_t)n);
      else if (n < 0 && !retryable()) { result = 1; break; }
    }
    if ((fds[1].revents & POLLOUT) && in_len) {
      ssize_t n = write(master, input, in_len);
      if (n > 0) consume(input, &in_len, (size_t)n);
      else if (n < 0 && !retryable() && errno != EIO) { result = 1; break; }
    }
    if ((fds[1].revents & (POLLIN | POLLHUP | POLLERR)) && out_len < CAP) {
      ssize_t n = read(master, output + out_len, CAP - out_len);
      if (n > 0) out_len += (size_t)n;
      else if (!n || (n < 0 && errno == EIO)) master_done = 1;
      else if (!retryable()) { perror("zen-terminal-pty: read PTY"); result = 1; break; }
    }
    if ((fds[0].revents & (POLLIN | POLLHUP | POLLERR)) && in_len < CAP && !master_done) {
      ssize_t n;
      if (remaining) {
        size_t count = remaining < CAP - in_len ? remaining : CAP - in_len;
        n = read(STDIN_FILENO, input + in_len, count);
        if (n > 0) { in_len += (size_t)n; remaining -= (size_t)n; }
      } else {
        char c;
        n = read(STDIN_FILENO, &c, 1);
        if (n > 0) {
          if (c != '\n') {
            if (header_len == sizeof(header) - 1 || c < ' ' || c > '~') goto malformed;
            header[header_len++] = c;
          } else {
            header[header_len] = 0;
            const char *p = header + 1;
            unsigned a, b;
            if (header_len && header[0] == 'I' && !number(&p, CAP, &a) && !*p) remaining = a;
            else if (header_len && header[0] == 'R' && !number(&p, MAX_DIM, &a) && a && *p++ == ' ' &&
                     !number(&p, MAX_DIM, &b) && b && !*p) {
              size.ws_row = (unsigned short)a; size.ws_col = (unsigned short)b;
              if (ioctl(master, TIOCSWINSZ, &size) < 0) { perror("zen-terminal-pty: resize"); result = 1; break; }
            } else goto malformed;
            header_len = 0;
          }
        }
      }
      if (!n) { if (remaining || header_len) goto malformed; break; }
      if (n < 0 && !retryable()) { perror("zen-terminal-pty: input"); result = 1; break; }
    }
    continue;
malformed:
    fprintf(stderr, "zen-terminal-pty: malformed or incomplete input frame\n"); result = 65; break;
  }
cleanup:
  close(master);
  reap(child, &status, &reaped);
  if (result) return result;
  if (stopping) return 128 + stopping;
  return WIFEXITED(status) ? WEXITSTATUS(status) : (WIFSIGNALED(status) ? 128 + WTERMSIG(status) : 1);
}
