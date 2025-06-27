const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require("@whiskeysockets/baileys");
const { Boom } = require("@hapi/boom");
const express = require("express");
const axios = require("axios");
const fs = require("fs");
const qrcode = require("qrcode-terminal");
require('dotenv').config();

// let botActive = true;
// const ownerNumber = "919426358505@s.whatsapp.net";

const startSock = async () => {
    const { state, saveCreds } = await useMultiFileAuthState("auth");

    const sock = makeWASocket({
        auth: state,
    });

    sock.ev.on("connection.update", (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log("Scan this QR code in WhatsApp:");
            generate(qr, { small: true });
        }

        if (connection === "close") {
            const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log("❌ Connection closed. Reconnecting?", shouldReconnect);
            if (shouldReconnect) {
                startSock();
            }
        } else if (connection === "open") {
            console.log("✅ Connected to WhatsApp!");
        }
    });

    sock.ev.on("creds.update", saveCreds);

    const TRIGGER_WORD = process.env.TRIGGER_WORD;// Activation keyword
    const END_TRIGGER_WORD = process.env.END_TRIGGER_WORD; //End-bot keyword

    let activeUsers = new Set(); // Track activated users
    let user_context = {};  // To track each user’s conversation state

    sock.ev.on("messages.upsert", async ({ messages, type }) => {
        if (type !== "notify") return;

        const msg = messages[0];
        if (!msg.message || msg.key.fromMe) return;

        const sender = msg.key.remoteJid;
        let text = "";

        if (msg.message?.conversation) {
            text = msg.message.conversation.trim();
        } else if (msg.message?.extendedTextMessage?.text) {
            text = msg.message.extendedTextMessage.text.trim();
        } else if (msg.message?.locationMessage) {
            const { degreesLatitude, degreesLongitude } = msg.message.locationMessage;
            const lat = degreesLatitude;
            const lng = degreesLongitude;

            // Only allow location if user is active
            if (!activeUsers.has(sender)) {
                console.log(`❌ Ignoring message from ${sender} - not activated`);
                return;
            }

            console.log(`📍 Location shared: ${lat}, ${lng}`);

            try {
                const res = await axios.post("http://127.0.0.1:5000/location", {
                    sender,
                    latitude: lat,
                    longitude: lng,
                });

                const reply = res.data.reply || "Couldn't fetch nearby places.";
                await sock.sendMessage(sender, { text: reply });
            } catch (err) {
                console.error("❌ Error from Python server:", err.message);
                await sock.sendMessage(sender, { text: "Server error while finding places." });
            }

            return;
        }

        if (!text) return;

        // Owner commands (no activation needed)
        // if (sender === ownerNumber) {
        //     const command = text.toLowerCase();
        //     if (command === "#off") {
        //         botActive = false;
        //         console.log("🛑 Bot turned OFF by owner");
        //         await sock.sendMessage(ownerNumber, { text: "🤖 Bot turned OFF." });
        //         return;
        //     }

        //     if (command === "#on") {
        //         botActive = true;
        //         console.log("✅ Bot turned ON by owner");
        //         await sock.sendMessage(ownerNumber, { text: "🤖 Bot turned ON." });
        //         return;
        //     }
        // }

        // if (!botActive) return;

        // Activation check
        if (text.toLowerCase() === TRIGGER_WORD) {
            if(activeUsers.has(sender)) {
                await sock.sendMessage(sender, { text: "🤖 Bot already activated and ready to help. Go ahead with your request!" });
                return;
            }

            await axios.post("http://127.0.0.1:5000/message", {
                sender,
                message: "end_session",
            });

            activeUsers.add(sender);
            user_context[sender] = "awaiting_option"; // Reset context
            const reply = (
                "👋 Hi! Welcome to TripGenie — your AI-powered travel assistant. \n\nType *‘start’* to explore nearby places or get a personalized itinerary!"
            );
            await sock.sendMessage(sender, { text: reply });
            return;
        }

        if (text.toLowerCase() === END_TRIGGER_WORD) {
            if(activeUsers.has(sender)) {
                await axios.post("http://127.0.0.1:5000/message", {
                    sender,
                    message: "end_session",
                });
                
                activeUsers.delete(sender);

            }
            user_context[sender] = "awaiting_option"; // Reset context
            const reply = (
                "👋 That’s it for now! TripGenie has signed off. \n Come back anytime to explore again."
            );
            await sock.sendMessage(sender, { text: reply });
            return;
        }

        // If user not activated yet, ignore message
        if (!activeUsers.has(sender)) {
            console.log(`❌ Ignoring message from ${sender} - not activated`);
            return;
        }

        console.log(`📨 Message from activated user ${sender}: ${text}`);

        try {
            // Forward message as it is to your Python backend for further handling
            const res = await axios.post("http://127.0.0.1:5000/message", {
                sender,
                message: text,
            });

            const reply = res.data.reply || "Sorry, couldn't process that.";
            await sock.sendMessage(sender, { text: reply });
        } catch (err) {
            console.error("❌ Error from Python server:", err.message);
            await sock.sendMessage(sender, { text: "❌ Server error. Try again later." });
        }
    });


};

startSock();
