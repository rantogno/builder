#!/bin/bash

# Testing wait function
# This can be used in the future to start fetch of all repos in
# parallel, and wait for specific ones to complete before starting to
# build them.

howmany()
{
   echo $#
}

waitall()
{
   local allpids=$@
   local runningpids=$allpids
   local donepids=""

   local total=$(howmany $allpids)
   local numdone=$(howmany $donepids)

   while [ $(howmany $runningpids) != 0 ]; do
      local oldpids=$runningpids
      wait -n $runningpids

      runningpids=""

      for p in $oldpids; do
         echo -n "Checking process ${p}: "
         if kill -0 $p 2>/dev/null; then
            echo "still running."
            runningpids+="$p "
         else
            echo "done"
            donepids+="$p "
         fi
      done
      numdone=$(howmany $donepids)
      echo "Number of finished processes: $numdone ($donepids)"
      echo "Running processes: ($runningpids)"
   done
}

pids=""
for t in 5 4 3; do
   sleep "$t" &
   pids="$pids $!"
done

waitall $pids
