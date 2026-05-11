# vhs tape for the csk demo GIF.
#
# Install vhs (https://github.com/charmbracelet/vhs) then:
#   vhs scripts/demo.tape
#
# Output is scripts/demo.gif — drop it in the README's hero slot.

Output scripts/demo.gif

Set FontSize 16
Set Width 1100
Set Height 680
Set Theme "Catppuccin Mocha"
Set TypingSpeed 35ms

Type "csk init --demo -y"
Enter
Sleep 800ms

Type@30ms "csk ask 'how many active subscriptions do we have, and what is our MRR?'"
Enter
Sleep 4s

Type "csk save mrr 'what is our MRR right now'"
Enter
Sleep 800ms

Type "csk queries"
Enter
Sleep 2s

Type "csk costs"
Enter
Sleep 3s
