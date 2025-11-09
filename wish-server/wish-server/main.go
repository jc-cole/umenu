package main

import (
	"log"
	"os/exec"

	"github.com/gliderlabs/ssh"
)

func main() {
	ssh.Handle(func(s ssh.Session) {
		cmd := exec.Command("/home/eat/.venv/bin/python",
			"/home/eat/umenu/umenu_cli.py", "shell")
		cmd.Stdin, cmd.Stdout, cmd.Stderr = s, s, s
		_ = cmd.Run()
	})

	log.Println("listening on :22")
	err := ssh.ListenAndServe(
		":22",
		nil,
		ssh.HostKeyFile("/home/eat/.ssh/host_ed25519"),
		ssh.NoClientAuth(true), // ← the only auth setting
	)
	if err != nil { log.Fatal(err) }
}
