# B200: Bad Code (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
root{she_is_not_a_machine_to_me}
```

## In short

An off-board bonus with no listing on the challenge board. A signature left in other challenges points to a hidden page on the CTF site. A character called Root talks to you there, checks that you really found her signature, and then leaves the flag somewhere that only exists when you ask for it: the browser console.

## Walkthrough

1. Find the signature. In [L100](../../../lab/L100-reduced-footprint/), the intruder's script ends with the comment `# signed: bad code`. The L100 brief tells you to remember it. The same signature appears again in a cleanup script elsewhere.
2. The brief for this challenge says someone else is on this domain and left a channel open. Try the signature as a page on the CTF site: `/badcode`.
3. The page starts as a cold Samaritan access panel, glitches, and is taken over by Root. She asks how you found her and what she left lying around.
4. Tell her. Any reply that mentions her signature ("bad code") earns her trust. Anything else and she asks again.
5. Once she trusts you, she says she will not print the flag on the page, because pages get read. She left it "somewhere that isn't really there until you ask for it".
6. Open the browser's developer tools and look at the page's script. It defines a function on the page called `root.unmask`.
7. Run `root.unmask()` in the console. Root prints a short message and the flag in the console, and it appears on the page as well.
8. Submit the flag on the board. Note the format: `root{...}`, not `number{...}`.

## Watch out for

- The page address is guessable from the challenge title alone. That is deliberate, to keep the bar low for a bonus.
- Reading the page source, running the function, or pasting the script into an AI assistant all work. There is no single intended route.
