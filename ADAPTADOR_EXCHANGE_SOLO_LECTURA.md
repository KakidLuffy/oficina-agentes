# Adaptador de exchange de solo lectura (diseño, NO implementado)

**Estado:** sin implementar. Hoy el sistema lee solo datos **públicos** de Kraken (velas, pares, mínimos), que no necesitan clave. No hay ninguna necesidad concreta de conectar una cuenta, y el usuario no ha autorizado ninguna configuración.

## Cuándo tendría sentido
Solo si en el futuro se quiere **comparar la simulación con saldos o comisiones reales de una cuenta propia** (p. ej. verificar el nivel de comisión real). Hasta que eso se pida y se autorice, no se implementa.

## Reglas de diseño (ya fijadas en `exchange_lectura.py`)
1. Solo métodos de consulta (`pares`, `velas`, `reglas`). **No existe** ningún método para crear, modificar o cancelar órdenes, ni para retirar o transferir fondos.
2. Una credencial solo se acepta si declara permisos **exclusivamente de «consulta»**; `comprobar_permisos` rechaza cualquier otro (trading, retirada, transferencia…).
3. Los datos de mercado solo salen de rutas **públicas** (`/0/public/…`); `comprobar_ruta_publica` rechaza el resto.
4. Las claves **nunca** van en el repositorio ni en el chat: se guardarían como secretos de GitHub (Settings → Secrets) con un permiso de solo consulta creado por el usuario en su exchange.
5. El adaptador no se importa desde el simulador ni desde el analista de IA: la conexión de lectura no puede convertirse en un mecanismo de ejecución.

## Lo que haría falta del usuario antes de implementarlo
- Confirmar la necesidad concreta.
- Crear en su exchange una clave **solo de consulta** (sin permisos de trading ni de retirada) y guardarla como secreto.
- Autorizar por escrito la configuración.
