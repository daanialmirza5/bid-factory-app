import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
    apiKey: "AIzaSyBOuRjBzvqNCFWWz6GFwTDIesDAZUa-lkc",
    authDomain: "bid-factory.firebaseapp.com",
    projectId: "bid-factory",
    storageBucket: "bid-factory.firebasestorage.app",
    messagingSenderId: "481946928301",
    appId: "1:481946928301:web:fa471480d11594c6cc3224"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
