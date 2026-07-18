FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

# --host 0.0.0.0 est indispensable en conteneur : par defaut le serveur Vite
# n'ecoute que sur localhost, injoignable depuis l'exterieur du conteneur.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
