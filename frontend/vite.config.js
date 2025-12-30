import { defineConfig } from 'vite'

import react from '@vitejs/plugin-react'



export default defineConfig({

  plugins: [react()],

  server: {

    proxy: {

      '/api': {

        target: 'http://10.99.111.19:8000',

        changeOrigin: true,

        secure: false,

        ws: true,

      },

    },

  },

})


