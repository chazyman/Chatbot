
./bin/ollama serve &

pid=$!

sleep 5


echo "Pulling llama3 and llama models"
ollama pull llava:7b
ollama pull llama3.1:8b

wait $pid
