/**
 * Modal reutilizável para exibir foto ampliada de pessoa com informações detalhadas.
 * Permite visualizar foto em tamanho grande, informações pessoais e navegar para ficha completa.
 */

function personPhotoModal(appState) {
  return {
    // Estado do modal
    showPhotoModal: false,
    photoUrl: null,
    pessoaId: null,
    pessoa: null,
    photoModalLoading: false,
    photoModalError: null,

    /**
     * Abre o modal com foto e carrega dados da pessoa.
     * @param {string} photoUrl - URL da foto a exibir
     * @param {number|string} pessoaId - ID da pessoa
     */
    openPhotoModal(photoUrl, pessoaId) {
      this.photoUrl = photoUrl;
      this.pessoaId = pessoaId;
      this.showPhotoModal = true;
      this.photoModalLoading = true;
      this.photoModalError = null;
      this.pessoa = null;
      this.fetchPessoaDetails(pessoaId);
    },

    /**
     * Fecha o modal e limpa o estado.
     */
    closePhotoModal() {
      this.showPhotoModal = false;
      setTimeout(() => {
        this.photoUrl = null;
        this.pessoaId = null;
        this.pessoa = null;
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
        const response = await api.get(`/pessoas/${pessoaId}`);
        this.pessoa = response.data;
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
      this.closePhotoModal();
      appState.navigate('pessoa-detalhe', this.pessoaId);
    },

    /**
     * Formata data de nascimento para exibição.
     * @param {string} data - Data em formato ISO
     * @param {string} suffix - Sufixo a adicionar (ex: "anos")
     * @returns {string} Data formatada
     */
    formatarNascimento(data, suffix = '') {
      if (!data) return '—';
      const d = new Date(data);
      const idade = new Date().getFullYear() - d.getFullYear();
      const meses = new Date().getMonth() - d.getMonth();
      const ajuste = meses < 0 ? 1 : 0;
      const idadeAtual = idade - ajuste;
      return `${d.toLocaleDateString('pt-BR')} (${idadeAtual} ${suffix ? suffix : 'anos'})`;
    },

    /**
     * Formata endereço de forma legível.
     * @param {object} endereco - Objeto endereço
     * @returns {string} Endereço formatado
     */
    formatEndereco(endereco) {
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
