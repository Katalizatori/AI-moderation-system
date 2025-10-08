
import api from './api'

export default {
  async getReviews() {
    const response = await api.get('/reviews/')
    return response.data
  },

  async createReview(content) {
    const response = await api.post('/reviews/', { content })
    return response.data
  }
}
