# T100: Satoshi (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{a6d72baa3db900b0}
```

## In short

The brief describes Bitcoin's first block, mined on 3 January 2009. Its creator embedded a newspaper headline in it. Hash that exact sentence and keep the first 16 characters.

## Walkthrough

1. Work out what the brief is describing. An anonymous creator, a first transmission on 3 January 2009, a sentence quoted from that morning's newspaper: this is the Bitcoin genesis block.
2. Look up the text embedded in the genesis block. It is: `The Times 03/Jan/2009 Chancellor on brink of second bailout for banks`
3. Take the SHA-256 of that exact sentence, with no line break at the end.
4. Keep the first 16 hex characters, in lowercase: `a6d72baa3db900b0`.
5. Wrap them in `number{}`.

## Watch out for

- The sentence has to be exact: same capital letters, same spacing, no full stop.
- A trailing newline changes the hash completely. On the command line, use `echo -n` or `printf` and not plain `echo`.
