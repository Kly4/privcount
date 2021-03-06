#!/bin/bash

set -e
set -u

# If you have privcount installed in a venv, activate it before running
# this script

# Process arguments
if [ $# -lt 1 -o $# -gt 2 ]; then
  echo "usage: $0 [-I] <privcount-directory>"
  echo "       -I: run 'pip install -I <privcount-directory>' before testing"
  exit 1
elif [ $# -eq 1 ]; then
  PRIVCOUNT_INSTALL=0
  PRIVCOUNT_DIRECTORY="$1"
elif [ $# -eq 2 ]; then
  PRIVCOUNT_INSTALL=1
  PRIVCOUNT_DIRECTORY="$2"
fi

if [ "$PRIVCOUNT_INSTALL" -eq 1 ]; then
  # Install the latest requirements
  # Unfortunately, this doesn't work on my OS X install without sudo
  #echo "Installing requirements from '$PRIVCOUNT_DIRECTORY' ..."
  #pip install -r "$PRIVCOUNT_DIRECTORY/requirements.txt"

  # Install the latest privcount version
  echo "Installing latest version of privcount from '$PRIVCOUNT_DIRECTORY' ..."
  pip install -I "$PRIVCOUNT_DIRECTORY"
fi

cd "$PRIVCOUNT_DIRECTORY/test"

# Run the python-based unit tests
echo "Testing time formatting:"
python test_format_time.py
echo ""

echo "Testing encryption:"
python test_encryption.py
echo ""

echo "Testing random numbers:"
python test_random.py
echo ""

echo "Testing counters:"
python test_counters.py
echo ""

# Requires a local privcount-patched Tor instance
#python test_tor_ctl_event.py

# Record how long the tests take to run
date
STARTSEC="`date +%s`"

# Move aside the old result files
echo "Moving old results files to '$PRIVCOUNT_DIRECTORY/test/old' ..."
mkdir -p old
mv privcount.* old/ || true

# Then run the injector, ts, sk, and dc
echo "Launching injector, tally server, share keeper, and data collector..."
privcount inject --simulate --port 20003 --log events.txt &
privcount ts config.yaml &
privcount sk config.yaml &
privcount dc config.yaml &

# Then wait for each job, terminating if any job produces an error
# Ideally, we'd want to use wait, or wait $job, but that only checks one job
# at a time, so continuing processes can cause the script to run forever
echo "Waiting for PrivCount to finish..."
JOB_STATUS=`jobs`
echo "$JOB_STATUS"
while echo "$JOB_STATUS" | grep -q "Running"; do
  # fail if any job has failed
  if echo "$JOB_STATUS" | grep -q "Exit"; then
    # and kill everything
    echo "Error: Privcount process exited with an error..."
    pkill -P $$
    exit 1
  fi
  # succeed if an outcome file is produced
  if [ -f privcount.outcome.*.json ]; then
    break
  fi
  sleep 2
  JOB_STATUS=`jobs`
  echo "$JOB_STATUS"
done

# Measure how long the actual tests took
ENDDATE=`date`
ENDSEC="`date +%s`"

# If an outcome file was produced, keep a link to the latest file
if [ -f privcount.outcome.*.json ]; then
  ln -s privcount.outcome.*.json privcount.outcome.latest.json
else
  echo "Error: No outcome file produced."
  pkill -P $$
  exit 1
fi

# If a tallies file was produced, keep a link to the latest file, and plot it
if [ -f privcount.tallies.*.json ]; then
  ln -s privcount.tallies.*.json privcount.tallies.latest.json
  echo "Plotting results..."
  # plot will fail if the optional dependencies are not installed
  # tolerate this failure, and shut down the privcount processes
  privcount plot -d privcount.tallies.latest.json data || true
else
  echo "Error: No tallies file produced."
  pkill -P $$
  exit 1
fi

# And terminate all the privcount processes
echo "Terminating privcount..."
pkill -P $$

# Show how long it took
echo "$ENDDATE"
ELAPSEDSEC=$[ $ENDSEC - $STARTSEC ]
echo "Seconds Elapsed: $ELAPSEDSEC"

# Show the differences between the latest and old latest outcome files
if [ -e privcount.outcome.latest.json -a \
     -e old/privcount.outcome.latest.json ]; then
  # there's no point in comparing the tallies JSON or results PDF
  echo "Comparing latest outcomes file with previous outcomes file..."
  # skip expected differences due to time or network jitter
  # some minor numeric differences are expected due to noise, and due to
  # events falling before or after data collection stops in short runs
  diff --minimal \
      -I "time" -I "[Cc]lock" -I "alive" -I "rtt" -I "Start" -I "Stop" \
      old/privcount.outcome.latest.json privcount.outcome.latest.json
else
  # Since we need old/latest and latest, it takes two runs to generate the
  # first outcome file comparison
  echo "Warning: Outcomes files could not be compared."
  echo "$0 must be run twice to produce the first comparison."
fi
