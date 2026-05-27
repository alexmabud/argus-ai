/**
 * Modal reutilizável para exibir foto ampliada de pessoa com informações detalhadas.
 * Permite visualizar foto em tamanho grande, informações pessoais e navegar para ficha completa.
 *
 * Uso nas páginas:
 *   x-data: "{ ...minhaPage(), ...personPhotoModal() }"
 *   Incluir no template: ${personPhotoModalHTML()}
 *   Acionar: openPhotoModal(fotoUrl, pessoaId, dadosPreview)
 *   dadosPreview: objeto com dados básicos já disponíveis no contexto (mostra imediatamente)
 */

/**
 * Retorna o HTML do modal para ser incluído nos templates das páginas.
 * Usa modalPessoa (não "pessoa") para evitar conflito com estado da página host.
 * @returns {string} HTML do modal
 */
function personPhotoModalHTML() {
  return `
    <div x-show="showPhotoModal" x-cloak @click="if($event.target === $el) closePhotoModal()"
         style="position: fixed; top: var(--header-height); left: 0; right: 0; bottom: var(--bottom-nav-height); background: rgba(5, 10, 15, 0.9); z-index: 60; display: flex; align-items: center; justify-content: center; padding: 0.75rem; backdrop-filter: blur(4px);">
      <div @click.stop
           style="display: flex; flex-direction: column; max-width: min(90vw, 540px); width: 100%; max-height: 100%; overflow: hidden; border-radius: 8px; background: var(--color-surface); border: 1px solid var(--color-border); box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);">

        <!-- Header -->
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.4rem 0.75rem; border-bottom: 1px solid var(--color-border); flex-shrink: 0;">
          <h3 style="font-family: var(--font-data); font-size: 0.75rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">Foto Ampliada</h3>
          <button @click="closePhotoModal()" class="hov-icon-danger" style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); font-size: 1.1rem; line-height: 1; padding: 0; width: 1.75rem; height: 1.75rem; display: flex; align-items: center; justify-content: center; transition: color 0.15s;">✕</button>
        </div>

        <!-- Conteúdo -->
        <div style="display: flex; flex-direction: column; gap: 0.75rem; padding: 0.75rem; overflow-y: auto; min-height: 0;">

          <!-- Foto -->
          <template x-if="photoUrl">
            <div style="display: flex; justify-content: center;">
              <img :src="photoUrl" style="width: 100%; max-height: 55vh; border-radius: 6px; object-fit: contain; display: block;">
            </div>
          </template>

          <!-- Loading (sem dados ainda) -->
          <template x-if="photoModalLoading && !modalPessoa">
            <div style="display: flex; justify-content: center; align-items: center; padding: 1rem;">
              <span class="spinner"></span>
            </div>
          </template>

          <!-- Erro -->
          <template x-if="photoModalError">
            <div style="padding: 0.75rem; background: var(--color-surface-hover); border-radius: 4px; border-left: 3px solid var(--color-danger);">
              <p style="color: var(--color-danger); margin: 0; font-size: 0.8rem;" x-text="photoModalError"></p>
            </div>
          </template>

          <!-- Dados do Veículo (opcional) -->
          <div x-show="modalVeiculo" style="display: flex; flex-direction: column; gap: 0.5rem;">
            <p style="font-family: var(--font-data); font-size: 0.7rem; font-weight: 600; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.1em; margin: 0;">Dados do Veículo</p>
            <div style="display: flex; flex-direction: column; gap: 0.4rem; padding: 0.75rem; background: var(--color-surface-hover); border-radius: 4px; border: 1px solid rgba(167,139,250,0.2);">
              <div x-show="modalVeiculo && modalVeiculo.placa"
                   style="display: flex; align-items: center; justify-content: space-between;">
                <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Placa</span>
                <span style="font-family: var(--font-data); font-weight: 700; color: var(--color-text); letter-spacing: 0.1em; background: var(--color-surface); padding: 0.125rem 0.5rem; border-radius: 2px; border: 1px solid var(--color-border);"
                      x-text="modalVeiculo && formatarPlaca(modalVeiculo.placa || '')"></span>
              </div>
              <div x-show="modalVeiculo && (modalVeiculo.modelo || modalVeiculo.cor || modalVeiculo.ano)"
                   style="display: flex; align-items: center; justify-content: space-between;">
                <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Veículo</span>
                <span style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.8rem;"
                      x-text="modalVeiculo && [modalVeiculo.modelo, modalVeiculo.cor, modalVeiculo.ano].filter(Boolean).join(' · ')"></span>
              </div>
            </div>
          </div>

          <!-- Divisor veículo → condutor -->
          <div x-show="modalVeiculo && modalPessoa" style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="flex: 1; height: 1px; background: var(--color-border);"></div>
            <span style="font-family: var(--font-data); font-size: 0.7rem; font-weight: 600; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.1em; white-space: nowrap;">Dados do Condutor</span>
            <div style="flex: 1; height: 1px; background: var(--color-border);"></div>
          </div>

          <!-- Dados da pessoa (mostra com dados preview ou dados completos) -->
          <div x-show="modalPessoa" style="display: flex; flex-direction: column; gap: 0.75rem;">

            <!-- Nome -->
            <div>
              <p style="font-family: var(--font-display); font-weight: 700; color: var(--color-text); text-transform: uppercase; margin: 0; font-size: 1.125rem;" x-text="modalPessoa && modalPessoa.nome"></p>
              <p x-show="modalPessoa && modalPessoa.apelido"
                 style="font-size: 0.8rem; color: var(--color-secondary); font-family: var(--font-data); margin: 0.25rem 0 0 0; font-style: italic;"
                 x-text="modalPessoa && ('Vulgo: ' + modalPessoa.apelido)"></p>
            </div>

            <!-- Divisor -->
            <div style="height: 1px; background: var(--color-border);"></div>

            <!-- Campos -->
            <div style="display: flex; flex-direction: column; gap: 0.5rem; font-size: 0.875rem;">

              <!-- CPF -->
              <div x-show="modalPessoa && (modalPessoa.cpf || modalPessoa.cpf_masked)"
                   style="display: flex; align-items: center; justify-content: space-between;">
                <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">CPF</span>
                <span style="color: var(--color-text-muted); font-family: var(--font-data); letter-spacing: 0.05em;"
                      x-text="modalPessoa && (modalPessoa.cpf || modalPessoa.cpf_masked)"></span>
              </div>

              <!-- Nascimento -->
              <div x-show="modalPessoa && modalPessoa.data_nascimento"
                   style="display: flex; align-items: center; justify-content: space-between;">
                <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Nascimento</span>
                <span style="color: var(--color-text-muted); font-family: var(--font-data);"
                      x-text="modalPessoa && formatarNascimentoModal(modalPessoa.data_nascimento)"></span>
              </div>

              <!-- Mãe -->
              <div x-show="modalPessoa && modalPessoa.nome_mae"
                   style="display: flex; align-items: center; justify-content: space-between;">
                <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Mãe</span>
                <span style="color: var(--color-text-muted); font-family: var(--font-data);"
                      x-text="modalPessoa && modalPessoa.nome_mae"></span>
              </div>

              <!-- Endereço -->
              <div x-show="modalPessoa && modalPessoa.enderecos && modalPessoa.enderecos.length > 0"
                   style="display: flex; flex-direction: column; gap: 0.25rem;">
                <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Endereço</span>
                <span style="color: var(--color-text-muted); font-family: var(--font-data); word-break: break-word;"
                      x-text="modalPessoa && modalPessoa.enderecos && formatEnderecoModal(modalPessoa.enderecos[0])"></span>
              </div>

              <!-- Observações -->
              <div x-show="modalPessoa && modalPessoa.observacoes"
                   style="display: flex; flex-direction: column; gap: 0.25rem; padding-top: 0.25rem;">
                <span style="color: var(--color-text-dim); font-family: var(--font-data); font-weight: 500; text-transform: uppercase; font-size: 0.75rem;">Observações</span>
                <p style="color: var(--color-text-muted); font-family: var(--font-data); margin: 0; font-size: 0.8rem; line-height: 1.4; word-break: break-word;"
                   x-text="modalPessoa && modalPessoa.observacoes"></p>
              </div>

              <!-- Loading mais dados -->
              <p x-show="photoModalLoading && modalPessoa"
                 style="font-size: 0.7rem; color: var(--color-text-dim); font-family: var(--font-data); margin: 0; text-align: center;">
                Carregando dados completos...
              </p>
            </div>
          </div>
        </div>

        <!-- Footer — Ver Ficha (primário/maior) | Fechar (vermelho) -->
        <div style="display: flex; gap: 0.5rem; padding: 1rem; border-top: 1px solid var(--color-border); background: var(--color-surface-hover); border-radius: 0 0 8px 8px; flex-shrink: 0;">
          <button @click="goToFichaPessoa()"
                  style="flex: 2; padding: 0.75rem; border-radius: 4px; background: var(--color-primary); color: var(--color-bg); border: none; font-family: var(--font-data); font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: all 0.15s; text-transform: uppercase; letter-spacing: 0.05em;"
                  class="hov-opacity-down">
            Ver Ficha Completa →
          </button>
          <button @click="closePhotoModal()"
                  style="flex: 1; padding: 0.75rem; border-radius: 4px; background: transparent; color: var(--color-danger); border: 1px solid var(--color-danger); font-family: var(--font-data); font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: all 0.15s; text-transform: uppercase; letter-spacing: 0.05em;"
                  class="hov-bg-danger-tint">
            Fechar
          </button>
        </div>
      </div>
    </div>
  `;
}

function personPhotoModal() {
  return {
    showPhotoModal: false,
    photoUrl: null,
    modalPessoaId: null,
    modalPessoa: null,
    modalVeiculo: null,
    photoModalLoading: false,
    photoModalError: null,

    /**
     * Abre o modal.
     * @param {string} photoUrl - URL da foto
     * @param {number|string} pessoaId - ID da pessoa
     * @param {object|null} previewData - Dados básicos já disponíveis (exibe imediatamente)
     * @param {object|null} veiculoData - Dados do veículo (opcional, exibe seção extra)
     */
    openPhotoModal(photoUrl, pessoaId, previewData, veiculoData) {
      this.photoUrl = photoUrl;
      this.modalPessoaId = pessoaId;
      this.showPhotoModal = true;
      this.photoModalError = null;
      this.modalPessoa = previewData || null;
      this.modalVeiculo = veiculoData || null;
      this.photoModalLoading = true;
      // Fetch dados completos em background
      this._fetchPessoaModal(pessoaId);
    },

    closePhotoModal() {
      this.showPhotoModal = false;
      setTimeout(() => {
        this.photoUrl = null;
        this.modalPessoaId = null;
        this.modalPessoa = null;
        this.modalVeiculo = null;
        this.photoModalLoading = false;
        this.photoModalError = null;
      }, 300);
    },

    async _fetchPessoaModal(pessoaId) {
      try {
        const data = await api.get(`/pessoas/${pessoaId}`);
        if (this.showPhotoModal) {
          this.modalPessoa = data;
        }
      } catch (error) {
        console.error('[personPhotoModal] Erro ao buscar pessoa:', error);
        if (this.showPhotoModal && !this.modalPessoa) {
          this.photoModalError = 'Erro ao carregar dados completos';
        }
      } finally {
        this.photoModalLoading = false;
      }
    },

    goToFichaPessoa() {
      const id = this.modalPessoaId;
      this.closePhotoModal();
      const appEl = document.querySelector('[x-data]');
      if (appEl?._x_dataStack) {
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].navigate('pessoa-detalhe');
      }
    },

    formatarNascimentoModal(data) {
      if (!data) return '—';
      const d = new Date(data + 'T00:00:00');
      const hoje = new Date();
      let idade = hoje.getFullYear() - d.getFullYear();
      if (hoje.getMonth() < d.getMonth() || (hoje.getMonth() === d.getMonth() && hoje.getDate() < d.getDate())) idade--;
      return `${d.toLocaleDateString('pt-BR')} (${idade} anos)`;
    },

    formatEnderecoModal(endereco) {
      if (!endereco) return '—';
      return [endereco.endereco, endereco.numero, endereco.complemento, endereco.bairro, endereco.cidade?.nome, endereco.estado?.sigla].filter(Boolean).join(', ');
    },
  };
}
