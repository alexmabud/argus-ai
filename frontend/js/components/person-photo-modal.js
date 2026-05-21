/**
 * Modal reutilizável para exibir foto ampliada de pessoa com informações detalhadas.
 * Permite visualizar foto em tamanho grande, informações pessoais e navegar para ficha completa.
 *
 * Uso nas páginas:
 *   x-data: "{ ...minhaPage(), ...personPhotoModal(window.app) }"
 *   Incluir no template: ${personPhotoModalHTML()}
 *   Acionar: openPhotoModal(fotoUrl, pessoaId)
 */

/**
 * Retorna o HTML do modal para ser incluído nos templates das páginas.
 * Usa modalPessoa (não "pessoa") para evitar conflito com dados da página host.
 * @returns {string} HTML do modal
 */
function personPhotoModalHTML() {
  return `
    <div x-show="showPhotoModal" x-cloak @click="if($event.target === $el) closePhotoModal()"
         style="position: fixed; inset: 0; background: rgba(5, 10, 15, 0.9); z-index: 60; display: flex; align-items: center; justify-content: center; padding: 1rem; backdrop-filter: blur(4px);">
      <div @click.stop
           style="display: flex; flex-direction: column; max-width: min(90vw, 540px); width: 100%; max-height: 90vh; overflow-y: auto; border-radius: 8px; background: var(--color-surface); border: 1px solid var(--color-border); box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);">

        <!-- Header -->
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 1rem; border-bottom: 1px solid var(--color-border); flex-shrink: 0;">
          <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">Foto Ampliada</h3>
          <button @click="closePhotoModal()" style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); font-size: 1.25rem; line-height: 1; padding: 0; width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; transition: color 0.15s;" onmouseover="this.style.color='var(--color-danger)'" onmouseout="this.style.color='var(--color-text-dim)'">✕</button>
        </div>

        <!-- Conteúdo -->
        <div style="display: flex; flex-direction: column; gap: 1rem; padding: 1rem; overflow-y: auto; flex: 1;">

          <!-- Loading -->
          <template x-if="photoModalLoading && !modalPessoa">
            <div style="display: flex; justify-content: center; align-items: center; padding: 2rem;">
              <span class="spinner"></span>
            </div>
          </template>

          <!-- Erro -->
          <template x-if="photoModalError && !photoModalLoading">
            <div style="padding: 1rem; background: var(--color-surface-hover); border-radius: 4px; border-left: 4px solid var(--color-danger);">
              <p style="color: var(--color-danger); margin: 0; font-size: 0.875rem;" x-text="photoModalError"></p>
            </div>
          </template>

          <!-- Foto -->
          <template x-if="photoUrl">
            <div style="display: flex; justify-content: center;">
              <img :src="photoUrl" style="width: 100%; max-height: 50vh; border-radius: 6px; object-fit: contain; display: block;">
            </div>
          </template>

          <!-- Dados da pessoa -->
          <template x-if="modalPessoa && !photoModalLoading">
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              <div>
                <p style="font-family: var(--font-display); font-weight: 700; color: var(--color-text); text-transform: uppercase; margin: 0; font-size: 1.125rem;" x-text="modalPessoa.nome"></p>
                <template x-if="modalPessoa.apelido">
                  <p style="font-size: 0.8rem; color: var(--color-secondary); font-family: var(--font-data); margin: 0.25rem 0 0 0; font-style: italic;" x-text="'Vulgo: ' + modalPessoa.apelido"></p>
                </template>
              </div>
              <div style="height: 1px; background: var(--color-border);"></div>
              <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.875rem;">
                <template x-if="modalPessoa.cpf || modalPessoa.cpf_masked">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">CPF</span>
                    <span style="color: var(--color-text-muted); font-family: var(--font-data); letter-spacing: 0.05em;" x-text="modalPessoa.cpf || modalPessoa.cpf_masked"></span>
                  </div>
                </template>
                <template x-if="modalPessoa.data_nascimento">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Nascimento</span>
                    <span style="color: var(--color-text-muted); font-family: var(--font-data);" x-text="formatarNascimentoModal(modalPessoa.data_nascimento)"></span>
                  </div>
                </template>
                <template x-if="modalPessoa.nome_mae">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Mãe</span>
                    <span style="color: var(--color-text-muted); font-family: var(--font-data);" x-text="modalPessoa.nome_mae"></span>
                  </div>
                </template>
                <template x-if="modalPessoa.enderecos && modalPessoa.enderecos.length > 0">
                  <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                    <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Endereço</span>
                    <span style="color: var(--color-text-muted); font-family: var(--font-data); word-break: break-word;" x-text="formatEnderecoModal(modalPessoa.enderecos[0])"></span>
                  </div>
                </template>
                <template x-if="modalPessoa.abordagens_count !== undefined">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Abordagens</span>
                    <span style="background: var(--color-primary); color: var(--color-bg); padding: 0.25rem 0.5rem; border-radius: 4px; font-family: var(--font-data); font-size: 0.75rem; font-weight: 600;" x-text="modalPessoa.abordagens_count"></span>
                  </div>
                </template>
                <template x-if="modalPessoa.observacoes">
                  <div style="display: flex; flex-direction: column; gap: 0.25rem; padding-top: 0.5rem;">
                    <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Observações</span>
                    <p style="color: var(--color-text-muted); font-family: var(--font-data); margin: 0; font-size: 0.8rem; line-height: 1.4; word-break: break-word;" x-text="modalPessoa.observacoes"></p>
                  </div>
                </template>
              </div>
            </div>
          </template>
        </div>

        <!-- Footer — Ver Ficha (primário/maior) | Fechar (vermelho) -->
        <div style="display: flex; gap: 0.5rem; padding: 1rem; border-top: 1px solid var(--color-border); background: var(--color-surface-hover); border-radius: 0 0 8px 8px; flex-shrink: 0;">
          <button @click="goToFichaPessoa()"
                  :disabled="!modalPessoa || photoModalLoading"
                  style="flex: 2; padding: 0.75rem; border-radius: 4px; background: var(--color-primary); color: var(--color-bg); border: none; font-family: var(--font-data); font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: all 0.15s; text-transform: uppercase; letter-spacing: 0.05em;"
                  onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'"
                  :style="(!modalPessoa || photoModalLoading) ? 'opacity: 0.4; cursor: not-allowed;' : ''">
            Ver Ficha Completa →
          </button>
          <button @click="closePhotoModal()"
                  style="flex: 1; padding: 0.75rem; border-radius: 4px; background: transparent; color: var(--color-danger); border: 1px solid var(--color-danger); font-family: var(--font-data); font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: all 0.15s; text-transform: uppercase; letter-spacing: 0.05em;"
                  onmouseover="this.style.background='rgba(255,59,48,0.1)'" onmouseout="this.style.background='transparent'">
            Fechar
          </button>
        </div>
      </div>
    </div>
  `;
}

function personPhotoModal(appState) {
  return {
    // Estado do modal — usa "modalPessoa" para não conflitar com "pessoa" das páginas host
    showPhotoModal: false,
    photoUrl: null,
    modalPessoaId: null,
    modalPessoa: null,
    photoModalLoading: false,
    photoModalError: null,

    /**
     * Abre o modal com foto e carrega dados da pessoa.
     * @param {string} photoUrl - URL da foto a exibir
     * @param {number|string} pessoaId - ID da pessoa
     */
    openPhotoModal(photoUrl, pessoaId) {
      this.photoUrl = photoUrl;
      this.modalPessoaId = pessoaId;
      this.showPhotoModal = true;
      this.photoModalLoading = true;
      this.photoModalError = null;
      this.modalPessoa = null;
      this.fetchPessoaDetails(pessoaId);
    },

    /**
     * Fecha o modal e limpa o estado.
     */
    closePhotoModal() {
      this.showPhotoModal = false;
      setTimeout(() => {
        this.photoUrl = null;
        this.modalPessoaId = null;
        this.modalPessoa = null;
        this.photoModalLoading = false;
        this.photoModalError = null;
      }, 300);
    },

    /**
     * Busca dados detalhados da pessoa via API.
     * @param {number|string} pessoaId - ID da pessoa
     */
    async fetchPessoaDetails(pessoaId) {
      try {
        this.photoModalLoading = true;
        this.photoModalError = null;
        this.modalPessoa = await api.get(`/pessoas/${pessoaId}`);
      } catch (error) {
        console.error('Erro ao buscar dados da pessoa:', error);
        this.photoModalError = 'Erro ao carregar dados da pessoa';
      } finally {
        this.photoModalLoading = false;
      }
    },

    /**
     * Navega para a ficha completa da pessoa e fecha o modal.
     */
    goToFichaPessoa() {
      const id = this.modalPessoaId;
      this.closePhotoModal();
      appState.navigate('pessoa-detalhe', id);
    },

    /**
     * Formata data de nascimento para exibição.
     * @param {string} data - Data em formato ISO
     * @returns {string} Data formatada
     */
    formatarNascimentoModal(data) {
      if (!data) return '—';
      const d = new Date(data);
      const hoje = new Date();
      let idade = hoje.getFullYear() - d.getFullYear();
      if (hoje.getMonth() < d.getMonth() || (hoje.getMonth() === d.getMonth() && hoje.getDate() < d.getDate())) idade--;
      return `${d.toLocaleDateString('pt-BR')} (${idade} anos)`;
    },

    /**
     * Formata endereço de forma legível.
     * @param {object} endereco - Objeto endereço
     * @returns {string} Endereço formatado
     */
    formatEnderecoModal(endereco) {
      if (!endereco) return '—';
      const partes = [
        endereco.endereco,
        endereco.numero ? `${endereco.numero}` : '',
        endereco.complemento,
        endereco.bairro,
        endereco.cidade?.nome,
        endereco.estado?.sigla,
      ];
      return partes.filter(Boolean).join(', ');
    },
  };
}
