package main

import (
	"io"
	"log"
	"os"
	"os/exec"

	"github.com/creack/pty"
	"github.com/gliderlabs/ssh"
	gossh "golang.org/x/crypto/ssh"
)

func main() {
	ssh.Handle(func(s ssh.Session) {
		ptyReq, winCh, hasPty := s.Pty()
		log.Printf("session start user=%s remote=%s pty=%v", s.User(), s.RemoteAddr(), hasPty)

		// run your CLI via bash -lc so PATH/venv behave like a login shell
		cmd := exec.Command("/bin/bash", "-lc",
			"/home/eat/.venv/bin/python /home/eat/umenu/umenu_cli.py shell")

		// base env
		term := "xterm"
		if hasPty && ptyReq.Term != "" {
			term = ptyReq.Term
		}
		cmd.Env = append(os.Environ(),
			"TERM="+term,
			"HOME=/home/eat",
			"PATH=/home/eat/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
		)

		if hasPty {
			// allocate a controlling TTY for the child
			ptmx, err := pty.Start(cmd)
			if err != nil {
				io.WriteString(s, "[umenu] failed to start PTY: "+err.Error()+"\n")
				log.Printf("pty start error: %v", err)
				return
			}
			defer func() { _ = ptmx.Close() }()

			// initial size + react to window resizes
			go func() {
				for w := range winCh {
					_ = pty.Setsize(ptmx, &pty.Winsize{
						Rows: uint16(w.Height),
						Cols: uint16(w.Width),
					})
				}
			}()
			_ = pty.Setsize(ptmx, &pty.Winsize{
				Rows: uint16(ptyReq.Window.Height),
				Cols: uint16(ptyReq.Window.Width),
			})

			// hook up IO (SSH <-> PTY)
			go func() { _, _ = io.Copy(ptmx, s) }()
			_, _ = io.Copy(s, ptmx)
		} else {
			// no PTY requested (non-interactive); just wire stdio
			cmd.Stdin, cmd.Stdout, cmd.Stderr = s, s, s
			if err := cmd.Run(); err != nil {
				io.WriteString(s, "[umenu] error: "+err.Error()+"\n")
				log.Printf("non-pty run error: %v", err)
			}
		}

		log.Printf("session end user=%s remote=%s", s.User(), s.RemoteAddr())
	})

	log.Println("listening on :22")
	err := ssh.ListenAndServe(
		":22",
		nil,
		ssh.HostKeyFile("/home/eat/.ssh/host_ed25519"),

		// accept any public key (instant for users with keys)
		ssh.PublicKeyAuth(func(ctx ssh.Context, key ssh.PublicKey) bool { return true }),

		// silent keyboard-interactive (one empty round-trip, then accept)
		ssh.KeyboardInteractiveAuth(func(ctx ssh.Context, ch gossh.KeyboardInteractiveChallenge) bool {
			_, _ = ch("", "", []string{}, []bool{})
			return true
		}),
	)
	if err != nil {
		log.Fatal(err)
	}
}
