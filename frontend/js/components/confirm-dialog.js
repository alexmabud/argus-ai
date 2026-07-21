/**
 * Modal de confirmação customizado e reutilizável, no estilo do app.
 * Substitui window.confirm() nativo nos fluxos de remoção (abordado,
 * veículo, foto), evitando exclusão acidental por clique único.
 *
 * Uso nas páginas:
 *   x-data: "{ ...minhaPage(), ...confirmDialog() }"
 *   Incluir no template: ${confirmDialogHTML()}
 *   Acionar: abrirConfirmacao('Remover X? Esta ação não pode ser desfeita.', () => { ... })
 */

/**
 * Retorna o HTML do modal para ser incluído nos templates das páginas.
 * @returns {string} HTML do modal
 */
function confirmDialogHTML() {
  return `
    <template x-teleport="body">
    <div x-show="confirmDialogVisible" x-cloak @click="if($event.target === $el) cancelarConfirmDialog()"
         style="position: fixed; top: var(--header-height); left: 0; right: 0; bottom: var(--bottom-nav-height); background: rgba(5, 10, 15, 0.9); z-index: 300; display: flex; align-items: center; justify-content: center; padding: 0.75rem; backdrop-filter: blur(4px);">
      <div @click.stop class="glass-card"
           style="display: flex; flex-direction: column; gap: 1rem; max-width: min(90vw, 400px); width: 100%; padding: 1.25rem; border: 1px solid var(--color-border); border-radius: 8px;">
        <p style="font-family: var(--font-body); font-size: 0.9rem; color: var(--color-text); margin: 0;"
           x-text="confirmDialogMensagem"></p>
        <div style="display: flex; gap: 0.5rem;">
          <button @click="cancelarConfirmDialog()"
                  style="flex: 1; padding: 0.625rem; border-radius: 4px; background: transparent; color: var(--color-text-muted); border: 1px solid var(--color-border); font-family: var(--font-data); font-size: 0.875rem; font-weight: 500; cursor: pointer; text-transform: uppercase; letter-spacing: 0.05em;">
            Cancelar
          </button>
          <button @click="confirmarConfirmDialog()"
                  style="flex: 1; padding: 0.625rem; border-radius: 4px; background: var(--color-danger); color: var(--color-bg); border: none; font-family: var(--font-data); font-size: 0.875rem; font-weight: 600; cursor: pointer; text-transform: uppercase; letter-spacing: 0.05em;">
            Remover
          </button>
        </div>
      </div>
    </div>
    </template>
  `;
}

function confirmDialog() {
  return {
    confirmDialogVisible: false,
    confirmDialogMensagem: '',
    _confirmDialogCallback: null,

    /**
     * Abre o modal de confirmação.
     * @param {string} mensagem - Mensagem exibida ao usuário.
     * @param {Function} callback - Chamado somente se o usuário confirmar.
     */
    abrirConfirmacao(mensagem, callback) {
      this.confirmDialogMensagem = mensagem;
      this._confirmDialogCallback = callback;
      this.confirmDialogVisible = true;
    },

    confirmarConfirmDialog() {
      const callback = this._confirmDialogCallback;
      this.confirmDialogVisible = false;
      this._confirmDialogCallback = null;
      if (callback) callback();
    },

    cancelarConfirmDialog() {
      this.confirmDialogVisible = false;
      this._confirmDialogCallback = null;
    },
  };
}
